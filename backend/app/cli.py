from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import os
import sys

from app.services.auth_service import create_user, delete_user, list_registered_users, update_user


_ANSI_RESET = "\033[0m"
_ANSI_BOLD = "\033[1m"
_ANSI_DIM = "\033[2m"
_ANSI_BURGUNDY_DARK = "\033[38;5;88m"
_ANSI_CYAN = "\033[36m"
_ANSI_GREEN = "\033[32m"
_ANSI_YELLOW = "\033[33m"
_ANSI_RED = "\033[31m"
_MOSCOW_TZ = timezone(timedelta(hours=3))


def _supports_color() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


def _paint(text: str, color: str, *, bold: bool = False, dim: bool = False, enabled: bool) -> str:
    if not enabled:
        return text
    prefixes: list[str] = []
    if bold:
        prefixes.append(_ANSI_BOLD)
    if dim:
        prefixes.append(_ANSI_DIM)
    prefixes.append(color)
    return f"{''.join(prefixes)}{text}{_ANSI_RESET}"


def _format_datetime_moscow(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    moscow_dt = parsed.astimezone(_MOSCOW_TZ)
    base = moscow_dt.strftime("%Y-%m-%d %H:%M:%S")
    offset_raw = moscow_dt.strftime("%z")
    offset = f"{offset_raw[:3]}:{offset_raw[3:]}" if len(offset_raw) == 5 else offset_raw
    return f"{base} {offset}"


def _print_users() -> int:
    users = list_registered_users()
    if not users:
        print("Пользователи не найдены")
        return 0

    use_color = _supports_color()

    headers = ["login", "display_name", "phone", "email", "failed", "total_failed_attempts", "locked_until", "created_at"]
    rows = [
        [
            user.login,
            user.display_name or "",
            user.phone or "",
            user.email or "",
            str(user.failed_attempts),
            str(user.total_failed_attempts),
            user.locked_until or "",
            _format_datetime_moscow(user.created_at),
        ]
        for user in users
    ]

    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    separator = " | "
    header_line = separator.join(header.ljust(widths[index]) for index, header in enumerate(headers))
    divider_line = "-+-".join("-" * width for width in widths)

    print(_paint(divider_line, _ANSI_CYAN, dim=True, enabled=use_color))
    print(_paint(header_line, _ANSI_BURGUNDY_DARK, bold=True, enabled=use_color))
    print(_paint(divider_line, _ANSI_CYAN, dim=True, enabled=use_color))
    for row, user in zip(rows, users):
        colored_cells = []
        for index, value in enumerate(row):
            cell_text = value.ljust(widths[index])
            color = _ANSI_GREEN
            bold = False

            if headers[index] == "login":
                color = _ANSI_YELLOW if user.login == "admin" else _ANSI_CYAN
                bold = True
            elif headers[index] == "failed":
                color = _ANSI_RED if user.failed_attempts > 0 else _ANSI_GREEN
            elif headers[index] == "total_failed_attempts":
                color = _ANSI_RED if user.total_failed_attempts > 0 else _ANSI_GREEN
            elif headers[index] == "locked_until":
                color = _ANSI_RED if value.strip() else _ANSI_GREEN
            elif headers[index] == "created_at":
                color = _ANSI_CYAN

            colored_cells.append(_paint(cell_text, color, bold=bold, enabled=use_color))

        print(separator.join(colored_cells))
    return 0


def _handle_add(args: argparse.Namespace) -> int:
    user = create_user(
        login=args.login,
        password=args.password,
        phone=args.phone,
        email=args.email,
        display_name=args.display_name,
    )
    print(f"Пользователь создан: {user.login}")
    return 0


def _handle_update(args: argparse.Namespace) -> int:
    if args.phone is not None and args.clear_phone:
        raise ValueError("Нельзя одновременно использовать --phone и --clear-phone")
    if args.email is not None and args.clear_email:
        raise ValueError("Нельзя одновременно использовать --email и --clear-email")
    if args.display_name is not None and args.clear_display_name:
        raise ValueError("Нельзя одновременно использовать --display-name и --clear-display-name")

    update_kwargs: dict[str, object] = {
        "login": args.login,
        "password": args.password,
        "unlock": args.unlock,
    }

    if args.phone is not None:
        update_kwargs["phone"] = args.phone
    if args.clear_phone:
        update_kwargs["phone"] = None

    if args.email is not None:
        update_kwargs["email"] = args.email
    if args.clear_email:
        update_kwargs["email"] = None

    if args.display_name is not None:
        update_kwargs["display_name"] = args.display_name
    if args.clear_display_name:
        update_kwargs["display_name"] = None

    user = update_user(**update_kwargs)
    print(f"Пользователь обновлен: {user.login}")
    return 0


def _handle_delete(args: argparse.Namespace) -> int:
    delete_user(login=args.login)
    print(f"Пользователь удален: {args.login}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Утилита администрирования пользователей",
    )

    top_subparsers = parser.add_subparsers(dest="entity")

    users_parser = top_subparsers.add_parser("users", help="Команды управления пользователями")
    users_subparsers = users_parser.add_subparsers(dest="action")

    list_parser = users_subparsers.add_parser("list", help="Распечатать список пользователей")
    list_parser.set_defaults(handler=lambda _: _print_users())

    add_parser = users_subparsers.add_parser("add", help="Добавить пользователя")
    add_parser.add_argument("--login", required=True, help="Логин")
    add_parser.add_argument("--password", required=True, help="Пароль (минимум 8 символов)")
    add_parser.add_argument("--phone", help="Телефон (опционально)")
    add_parser.add_argument("--email", help="Email (опционально)")
    add_parser.add_argument("--display-name", help="Отображаемое имя (опционально)")
    add_parser.set_defaults(handler=_handle_add)

    update_parser = users_subparsers.add_parser("update", help="Изменить пользователя")
    update_parser.add_argument("--login", required=True, help="Логин")
    update_parser.add_argument("--password", help="Новый пароль")
    update_parser.add_argument("--phone", help="Новый телефон")
    update_parser.add_argument("--email", help="Новый email")
    update_parser.add_argument("--display-name", help="Новое отображаемое имя")
    update_parser.add_argument("--clear-phone", action="store_true", help="Очистить телефон")
    update_parser.add_argument("--clear-email", action="store_true", help="Очистить email")
    update_parser.add_argument("--clear-display-name", action="store_true", help="Сбросить отображаемое имя")
    update_parser.add_argument("--unlock", action="store_true", help="Сбросить блокировку и счетчик неудачных входов")
    update_parser.set_defaults(handler=_handle_update)

    delete_parser = users_subparsers.add_parser("delete", help="Удалить пользователя")
    delete_parser.add_argument("--login", required=True, help="Логин")
    delete_parser.set_defaults(handler=_handle_delete)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "handler"):
        parser.print_help()
        return 1

    try:
        return int(args.handler(args))
    except ValueError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
