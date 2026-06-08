from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
from io import BytesIO
from pathlib import Path
import secrets
import sqlite3
import threading
import uuid

import qrcode

from app.config import settings
from app.schemas import (
    AuthSuccessResponse,
    PasswordLoginRequest,
    QrConfirmRequest,
    QrCreateResponse,
    QrStatusResponse,
    RegistrationConfirmRequest,
    RegistrationStartRequest,
    RegistrationStartResponse,
    RegistrationValidateRequest,
    RegistrationValidateResponse,
    SmsSendRequest,
    SmsSendResponse,
    SmsVerifyRequest,
)


_ACCESS_TOKEN_TTL_SECONDS = 3600
_SMS_TTL_SECONDS = 300
_QR_TTL_SECONDS = 180
_REG_TTL_SECONDS = 600
_MAX_FAILED_LOGIN_ATTEMPTS = 5
_LOGIN_LOCK_SECONDS = 300
_UNSET = object()


class AuthLockedError(ValueError):
    pass


@dataclass
class SmsChallenge:
    code: str
    expires_at: datetime


@dataclass
class QrSession:
    session_id: str
    payload: str
    image_data_url: str
    status: str
    expires_at: datetime
    access_token: str | None = None


@dataclass
class UserAdminRecord:
    login: str
    display_name: str | None
    role: str
    phone: str | None
    email: str | None
    failed_attempts: int
    total_failed_attempts: int
    locked_until: str | None
    created_at: str


@dataclass
class TokenPrincipal:
    login: str
    role: str
    expires_at: datetime


_LOCK = threading.RLock()
_SMS_CHALLENGES: dict[str, SmsChallenge] = {}
_QR_SESSIONS: dict[str, QrSession] = {}
_ACCESS_TOKENS: dict[str, TokenPrincipal] = {}


def _get_connection() -> sqlite3.Connection:
    db_path = Path(settings.storage_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 150_000)
    return digest.hex()


def _new_password_digest(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    return _hash_password(password, salt), salt


def _verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate = _hash_password(password, salt)
    return secrets.compare_digest(candidate, password_hash)


def _mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    prefix = local[:2] if len(local) >= 2 else local[:1]
    return f"{prefix}{'*' * max(1, len(local) - len(prefix))}@{domain}"


def _validate_registration_fields(login: str, password: str, phone: str | None, email: str | None) -> list[str]:
    errors: list[str] = []

    normalized_login = login.strip()
    if len(normalized_login) < 3:
        errors.append("Логин должен содержать минимум 3 символа")
    if not all(char.isalnum() or char in {"_", "-", "."} for char in normalized_login):
        errors.append("Логин может содержать только буквы, цифры, _, -, .")

    if len(password) < 8:
        errors.append("Пароль должен содержать минимум 8 символов")

    has_phone = bool(phone and phone.strip())
    has_email = bool(email and email.strip())
    if has_phone == has_email:
        errors.append("Укажите только один канал подтверждения: номер телефона или email")

    if has_email and ("@" not in (email or "") or "." not in (email or "")):
        errors.append("Некорректный формат email")

    return errors


def _normalize_login(login: str) -> str:
    return login.strip()


def _validate_login_format(login: str) -> list[str]:
    errors: list[str] = []
    if len(login) < 3:
        errors.append("Логин должен содержать минимум 3 символа")
    if not all(char.isalnum() or char in {"_", "-", "."} for char in login):
        errors.append("Логин может содержать только буквы, цифры, _, -, .")
    return errors


def _normalize_phone(phone: str | None) -> str | None:
    if phone is None:
        return None
    normalized = phone.strip()
    return normalized or None


def _normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    normalized = email.strip().lower()
    return normalized or None


def _validate_email_format(email: str | None) -> list[str]:
    if not email:
        return []
    if "@" not in email or "." not in email:
        return ["Некорректный формат email"]
    return []


def _row_to_user_admin_record(row: sqlite3.Row) -> UserAdminRecord:
    return UserAdminRecord(
        login=row["login"],
        display_name=row["display_name"],
        role=row["role"] or "user",
        phone=row["phone"],
        email=row["email"],
        failed_attempts=int(row["failed_attempts"] or 0),
        total_failed_attempts=int(row["total_failed_attempts"] or 0),
        locked_until=row["locked_until"],
        created_at=row["created_at"],
    )


def _get_user_row(login: str) -> sqlite3.Row | None:
    with _get_connection() as connection:
        return connection.execute(
            """
            SELECT login, display_name, role, phone, email, failed_attempts, total_failed_attempts, locked_until, created_at
            FROM users
            WHERE login = ?
            """,
            (login,),
        ).fetchone()


def list_registered_users() -> list[UserAdminRecord]:
    ensure_auth_storage()
    with _get_connection() as connection:
        rows = connection.execute(
            """
            SELECT login, display_name, role, phone, email, failed_attempts, total_failed_attempts, locked_until, created_at
            FROM users
            ORDER BY datetime(created_at) ASC, login ASC
            """
        ).fetchall()
    return [_row_to_user_admin_record(row) for row in rows]


def create_user(
    login: str,
    password: str,
    *,
    role: str = "user",
    phone: str | None = None,
    email: str | None = None,
    display_name: str | None = None,
) -> UserAdminRecord:
    ensure_auth_storage()
    normalized_login = _normalize_login(login)
    normalized_phone = _normalize_phone(phone)
    normalized_email = _normalize_email(email)
    normalized_display_name = (display_name or "").strip() or normalized_login
    normalized_role = "admin" if role == "admin" else "user"

    errors = _validate_login_format(normalized_login)
    if len(password) < 8:
        errors.append("Пароль должен содержать минимум 8 символов")
    errors.extend(_validate_email_format(normalized_email))
    if normalized_phone and normalized_email:
        errors.append("Пользователь может иметь только один канал: телефон или email")
    if _is_login_taken(normalized_login):
        errors.append("Логин уже занят")
    if _is_contact_taken(normalized_phone, normalized_email):
        errors.append("Указанный телефон или email уже используется")
    if errors:
        raise ValueError("; ".join(errors))

    password_hash, salt = _new_password_digest(password)
    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO users(
                login, password_hash, salt, role, phone, email, display_name,
                failed_attempts, total_failed_attempts, locked_until, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, NULL, ?)
            """,
            (
                normalized_login,
                password_hash,
                salt,
                normalized_role,
                normalized_phone,
                normalized_email,
                normalized_display_name,
                _utcnow().isoformat(),
            ),
        )

    created_row = _get_user_row(normalized_login)
    if created_row is None:
        raise ValueError("Не удалось создать пользователя")
    return _row_to_user_admin_record(created_row)


def update_user(
    login: str,
    *,
    password: str | None = None,
    role: str | object = _UNSET,
    phone: str | None | object = _UNSET,
    email: str | None | object = _UNSET,
    display_name: str | None | object = _UNSET,
    unlock: bool = False,
) -> UserAdminRecord:
    ensure_auth_storage()
    normalized_login = _normalize_login(login)

    with _get_connection() as connection:
        existing = connection.execute(
            """
            SELECT login, password_hash, salt, role, phone, email, display_name, failed_attempts, locked_until
            FROM users
            WHERE login = ?
            """,
            (normalized_login,),
        ).fetchone()
        if existing is None:
            raise ValueError("Пользователь не найден")

        next_phone = existing["phone"] if phone is _UNSET else _normalize_phone(phone)
        next_email = existing["email"] if email is _UNSET else _normalize_email(email)
        next_display_name = existing["display_name"] if display_name is _UNSET else (display_name or "").strip()
        next_role = existing["role"] if role is _UNSET else ("admin" if role == "admin" else "user")
        if not next_display_name:
            next_display_name = normalized_login

        errors: list[str] = []
        if password is not None and len(password) < 8:
            errors.append("Пароль должен содержать минимум 8 символов")
        errors.extend(_validate_email_format(next_email))
        if next_phone and next_email:
            errors.append("Пользователь может иметь только один канал: телефон или email")

        if next_phone and next_phone != existing["phone"]:
            phone_row = connection.execute(
                "SELECT login FROM users WHERE phone = ? AND login <> ?",
                (next_phone, normalized_login),
            ).fetchone()
            if phone_row is not None:
                errors.append("Указанный телефон уже используется")

        if next_email and next_email != existing["email"]:
            email_row = connection.execute(
                "SELECT login FROM users WHERE email = ? AND login <> ?",
                (next_email, normalized_login),
            ).fetchone()
            if email_row is not None:
                errors.append("Указанный email уже используется")

        if errors:
            raise ValueError("; ".join(errors))

        next_password_hash = existing["password_hash"]
        next_salt = existing["salt"]
        if password is not None:
            next_password_hash, next_salt = _new_password_digest(password)

        next_failed_attempts = 0 if unlock else int(existing["failed_attempts"] or 0)
        next_locked_until = None if unlock else existing["locked_until"]

        connection.execute(
            """
            UPDATE users
            SET password_hash = ?,
                salt = ?,
                role = ?,
                phone = ?,
                email = ?,
                display_name = ?,
                failed_attempts = ?,
                locked_until = ?
            WHERE login = ?
            """,
            (
                next_password_hash,
                next_salt,
                next_role,
                next_phone,
                next_email,
                next_display_name,
                next_failed_attempts,
                next_locked_until,
                normalized_login,
            ),
        )

    updated_row = _get_user_row(normalized_login)
    if updated_row is None:
        raise ValueError("Пользователь не найден")
    return _row_to_user_admin_record(updated_row)


def delete_user(login: str) -> bool:
    ensure_auth_storage()
    normalized_login = _normalize_login(login)
    with _get_connection() as connection:
        deleted = connection.execute(
            "DELETE FROM users WHERE login = ?",
            (normalized_login,),
        ).rowcount
    if not deleted:
        raise ValueError("Пользователь не найден")
    return True


def ensure_auth_storage() -> None:
    with _get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                login TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                phone TEXT UNIQUE,
                email TEXT UNIQUE,
                display_name TEXT,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                total_failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS registration_challenges (
                challenge_id TEXT PRIMARY KEY,
                login TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                code TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_registration_challenges_login
            ON registration_challenges(login);
            """
        )

        user_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        if "failed_attempts" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0")
        if "total_failed_attempts" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN total_failed_attempts INTEGER NOT NULL DEFAULT 0")
        if "locked_until" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN locked_until TEXT")
        if "role" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
            connection.execute("UPDATE users SET role = 'user' WHERE role IS NULL OR role = ''")

        admin_row = connection.execute("SELECT login FROM users WHERE login = ?", ("admin",)).fetchone()
        if admin_row is None:
            password_hash, salt = _new_password_digest("admin123")
            connection.execute(
                """
                INSERT INTO users(
                    login, password_hash, salt, role, phone, email, display_name,
                    failed_attempts, total_failed_attempts, locked_until, created_at
                )
                VALUES (?, ?, ?, 'admin', NULL, NULL, ?, 0, 0, NULL, ?)
                """,
                ("admin", password_hash, salt, "Администратор", _utcnow().isoformat()),
            )
        else:
            connection.execute("UPDATE users SET role = 'admin' WHERE login = 'admin'")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


def _issue_access_token(login: str, role: str) -> str:
    token = _generate_token()
    expires_at = _utcnow() + timedelta(seconds=_ACCESS_TOKEN_TTL_SECONDS)
    with _LOCK:
        _cleanup_expired()
        _ACCESS_TOKENS[token] = TokenPrincipal(login=login, role=role, expires_at=expires_at)
    return token


def get_token_principal(access_token: str) -> TokenPrincipal | None:
    with _LOCK:
        _cleanup_expired()
        principal = _ACCESS_TOKENS.get(access_token)
        if principal is None:
            return None
        if principal.expires_at <= _utcnow():
            _ACCESS_TOKENS.pop(access_token, None)
            return None
        return principal


def _mask_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 4:
        return "***"
    return f"+*** *** ** {digits[-2:]}"


def _cleanup_expired() -> None:
    now = _utcnow()
    expired_phones = [phone for phone, challenge in _SMS_CHALLENGES.items() if challenge.expires_at <= now]
    for phone in expired_phones:
        _SMS_CHALLENGES.pop(phone, None)

    expired_sessions = [
        session_id for session_id, session in _QR_SESSIONS.items() if session.expires_at <= now and session.status != "confirmed"
    ]
    for session_id in expired_sessions:
        session = _QR_SESSIONS.get(session_id)
        if session:
            session.status = "expired"

    expired_tokens = [token for token, principal in _ACCESS_TOKENS.items() if principal.expires_at <= now]
    for token in expired_tokens:
        _ACCESS_TOKENS.pop(token, None)

    with _get_connection() as connection:
        connection.execute(
            "DELETE FROM registration_challenges WHERE expires_at <= ?",
            (_utcnow().isoformat(),),
        )


def _is_login_taken(login: str) -> bool:
    with _get_connection() as connection:
        row = connection.execute("SELECT login FROM users WHERE login = ?", (login,)).fetchone()
    return row is not None


def _is_contact_taken(phone: str | None, email: str | None) -> bool:
    with _get_connection() as connection:
        if phone:
            row = connection.execute("SELECT login FROM users WHERE phone = ?", (phone,)).fetchone()
            if row is not None:
                return True
        if email:
            row = connection.execute("SELECT login FROM users WHERE email = ?", (email,)).fetchone()
            if row is not None:
                return True
    return False


def login_with_password(payload: PasswordLoginRequest) -> AuthSuccessResponse:
    ensure_auth_storage()
    now = _utcnow()
    with _get_connection() as connection:
        row = connection.execute(
            "SELECT login, password_hash, salt, role, display_name, failed_attempts, total_failed_attempts, locked_until FROM users WHERE login = ?",
            (payload.login,),
        ).fetchone()

    if row is not None and row["locked_until"]:
        locked_until = datetime.fromisoformat(row["locked_until"])
        if locked_until > now:
            retry_after = max(1, int((locked_until - now).total_seconds()))
            raise AuthLockedError(f"Аккаунт временно заблокирован. Повторите через {retry_after} сек.")

    if row is None or not _verify_password(payload.password, row["password_hash"], row["salt"]):
        if row is not None:
            attempts = int(row["failed_attempts"] or 0) + 1
            total_attempts = int(row["total_failed_attempts"] or 0) + 1
            lock_until_value: str | None = None
            if attempts >= _MAX_FAILED_LOGIN_ATTEMPTS:
                lock_until_value = (now + timedelta(seconds=_LOGIN_LOCK_SECONDS)).isoformat()
            with _get_connection() as connection:
                connection.execute(
                    "UPDATE users SET failed_attempts = ?, total_failed_attempts = ?, locked_until = ? WHERE login = ?",
                    (attempts, total_attempts, lock_until_value, payload.login),
                )
            if lock_until_value is not None:
                raise AuthLockedError(f"Слишком много неверных попыток. Вход заблокирован на {_LOGIN_LOCK_SECONDS} сек.")
        raise ValueError("Неверный логин или пароль")

    with _get_connection() as connection:
        connection.execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE login = ?",
            (payload.login,),
        )

    return AuthSuccessResponse(
        success=True,
        method="password",
        access_token=_issue_access_token(payload.login, row["role"] or "user"),
        expires_in=_ACCESS_TOKEN_TTL_SECONDS,
        display_name=row["display_name"] or payload.login,
        role=row["role"] or "user",
    )


def send_sms_code(payload: SmsSendRequest) -> SmsSendResponse:
    ensure_auth_storage()
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = _utcnow() + timedelta(seconds=_SMS_TTL_SECONDS)

    with _LOCK:
        _cleanup_expired()
        _SMS_CHALLENGES[payload.phone] = SmsChallenge(code=code, expires_at=expires_at)

    return SmsSendResponse(
        success=True,
        phone_masked=_mask_phone(payload.phone),
        expires_in=_SMS_TTL_SECONDS,
        demo_code=code,
    )


def verify_sms_code(payload: SmsVerifyRequest) -> AuthSuccessResponse:
    ensure_auth_storage()
    with _LOCK:
        _cleanup_expired()
        challenge = _SMS_CHALLENGES.get(payload.phone)
        if challenge is None:
            raise ValueError("Код не найден или истек")
        if challenge.code != payload.code:
            raise ValueError("Неверный код подтверждения")
        _SMS_CHALLENGES.pop(payload.phone, None)

    return AuthSuccessResponse(
        success=True,
        method="sms",
        access_token=_issue_access_token(f"sms:{payload.phone}", "user"),
        expires_in=_ACCESS_TOKEN_TTL_SECONDS,
        display_name="Пользователь",
        role="user",
    )


def _render_qr_data_url(payload: str) -> str:
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def create_qr_session() -> QrCreateResponse:
    ensure_auth_storage()
    session_id = str(uuid.uuid4())
    payload = f"otd-auth://qr-login?session_id={session_id}"
    image_data_url = _render_qr_data_url(payload)
    expires_at = _utcnow() + timedelta(seconds=_QR_TTL_SECONDS)

    with _LOCK:
        _cleanup_expired()
        _QR_SESSIONS[session_id] = QrSession(
            session_id=session_id,
            payload=payload,
            image_data_url=image_data_url,
            status="pending",
            expires_at=expires_at,
        )

    return QrCreateResponse(
        session_id=session_id,
        qr_payload=payload,
        qr_image_data_url=image_data_url,
        expires_in=_QR_TTL_SECONDS,
    )


def check_qr_status(session_id: str) -> QrStatusResponse:
    ensure_auth_storage()
    with _LOCK:
        _cleanup_expired()
        session = _QR_SESSIONS.get(session_id)
        if session is None:
            raise ValueError("QR-сессия не найдена")

        return QrStatusResponse(
            session_id=session_id,
            status=session.status,
            access_token=session.access_token,
            expires_in=max(0, int((session.expires_at - _utcnow()).total_seconds())),
        )


def confirm_qr_session(payload: QrConfirmRequest) -> AuthSuccessResponse:
    ensure_auth_storage()
    with _LOCK:
        _cleanup_expired()
        session = _QR_SESSIONS.get(payload.session_id)
        if session is None:
            raise ValueError("QR-сессия не найдена")
        if session.status == "expired":
            raise ValueError("QR-сессия истекла")
        if session.status != "confirmed":
            session.status = "confirmed"
            session.access_token = _issue_access_token(f"qr:{session.session_id}", "user")

    return AuthSuccessResponse(
        success=True,
        method="qr",
        access_token=session.access_token or _issue_access_token(f"qr:{session.session_id}", "user"),
        expires_in=_ACCESS_TOKEN_TTL_SECONDS,
        display_name="Пользователь",
        role="user",
    )


def validate_registration(payload: RegistrationValidateRequest) -> RegistrationValidateResponse:
    ensure_auth_storage()
    login = payload.login.strip()
    phone = payload.phone.strip() if payload.phone else None
    email = payload.email.strip().lower() if payload.email else None

    errors = _validate_registration_fields(login, payload.password, phone, email)
    login_available = not _is_login_taken(login)
    if not login_available:
        errors.append("Логин уже занят")
    if _is_contact_taken(phone, email):
        errors.append("Указанный телефон или email уже используется")

    return RegistrationValidateResponse(
        valid=not errors,
        login_available=login_available,
        errors=errors,
    )


def start_registration(payload: RegistrationStartRequest) -> RegistrationStartResponse:
    ensure_auth_storage()
    login = payload.login.strip()
    phone = payload.phone.strip() if payload.phone else None
    email = payload.email.strip().lower() if payload.email else None

    validation = validate_registration(
        RegistrationValidateRequest(
            login=login,
            password=payload.password,
            phone=phone,
            email=email,
        )
    )
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))

    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge_id = str(uuid.uuid4())
    password_hash, salt = _new_password_digest(payload.password)
    expires_at = _utcnow() + timedelta(seconds=_REG_TTL_SECONDS)

    with _LOCK:
        _cleanup_expired()
        with _get_connection() as connection:
            connection.execute("DELETE FROM registration_challenges WHERE login = ?", (login,))
            connection.execute(
                """
                INSERT INTO registration_challenges(
                    challenge_id, login, password_hash, salt, phone, email, code, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    challenge_id,
                    login,
                    password_hash,
                    salt,
                    phone,
                    email,
                    code,
                    expires_at.isoformat(),
                    _utcnow().isoformat(),
                ),
            )

    contact_masked = _mask_phone(phone or "") if phone else _mask_email(email or "")
    return RegistrationStartResponse(
        challenge_id=challenge_id,
        contact_masked=contact_masked,
        expires_in=_REG_TTL_SECONDS,
        demo_code=code,
    )


def confirm_registration(payload: RegistrationConfirmRequest) -> AuthSuccessResponse:
    ensure_auth_storage()
    registered_login: str | None = None
    with _LOCK:
        _cleanup_expired()
        with _get_connection() as connection:
            row = connection.execute(
                """
                SELECT challenge_id, login, password_hash, salt, phone, email, code, expires_at
                FROM registration_challenges
                WHERE challenge_id = ?
                """,
                (payload.challenge_id,),
            ).fetchone()

            if row is None:
                raise ValueError("Сценарий регистрации не найден или истек")

            if row["expires_at"] <= _utcnow().isoformat():
                connection.execute("DELETE FROM registration_challenges WHERE challenge_id = ?", (payload.challenge_id,))
                raise ValueError("Код подтверждения истек")

            if row["code"] != payload.code:
                raise ValueError("Неверный код подтверждения")

            existing_login_row = connection.execute(
                "SELECT login FROM users WHERE login = ?",
                (row["login"],),
            ).fetchone()
            if existing_login_row is not None:
                connection.execute("DELETE FROM registration_challenges WHERE challenge_id = ?", (payload.challenge_id,))
                raise ValueError("Логин уже зарегистрирован")

            existing_contact_row = None
            if row["phone"]:
                existing_contact_row = connection.execute(
                    "SELECT login FROM users WHERE phone = ?",
                    (row["phone"],),
                ).fetchone()
            if existing_contact_row is None and row["email"]:
                existing_contact_row = connection.execute(
                    "SELECT login FROM users WHERE email = ?",
                    (row["email"],),
                ).fetchone()
            if existing_contact_row is not None:
                connection.execute("DELETE FROM registration_challenges WHERE challenge_id = ?", (payload.challenge_id,))
                raise ValueError("Телефон или email уже используется")

            connection.execute(
                """
                INSERT INTO users(login, password_hash, salt, role, phone, email, display_name, created_at)
                VALUES (?, ?, ?, 'user', ?, ?, ?, ?)
                """,
                (
                    row["login"],
                    row["password_hash"],
                    row["salt"],
                    row["phone"],
                    row["email"],
                    row["login"],
                    _utcnow().isoformat(),
                ),
            )
            registered_login = row["login"]
            connection.execute("DELETE FROM registration_challenges WHERE challenge_id = ?", (payload.challenge_id,))

    return AuthSuccessResponse(
        success=True,
        method="registration",
        access_token=_issue_access_token(registered_login or "registered-user", "user"),
        expires_in=_ACCESS_TOKEN_TTL_SECONDS,
        display_name=registered_login or "Пользователь",
        role="user",
    )
