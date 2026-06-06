from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
import logging
import time
from opensearchpy import OpenSearch

from app.schemas import (
    AdminUserCreateRequest,
    AdminUserDeleteResponse,
    AdminUserRecord,
    AdminUserUpdateRequest,
    AiFeedbackRequest,
    AiFeedbackResponse,
    AiAskRequest,
    AiAskResponse,
    AuthSuccessResponse,
    DocumentRecord,
    DocumentTreeResponse,
    DocumentUploadResponse,
    IndexBootstrapResponse,
    KpiResponse,
    PasswordLoginRequest,
    RegistrationConfirmRequest,
    RegistrationStartRequest,
    RegistrationStartResponse,
    RegistrationValidateRequest,
    RegistrationValidateResponse,
    QrConfirmRequest,
    QrCreateResponse,
    QrStatusResponse,
    SearchRequest,
    SearchResponse,
    SmsSendRequest,
    SmsSendResponse,
    SmsVerifyRequest,
)
from app.services.ai_service import ask_ai
from app.services.auth_service import (
    AuthLockedError,
    check_qr_status,
    confirm_registration,
    confirm_qr_session,
    create_user,
    create_qr_session,
    delete_user,
    get_token_principal,
    list_registered_users,
    login_with_password,
    start_registration,
    send_sms_code,
    TokenPrincipal,
    update_user,
    validate_registration,
    verify_sms_code,
)
from app.services.document_service import (
    bootstrap_index,
    create_gotd_archive,
    get_document,
    get_document_tree,
    ingest_document,
)
from app.services.metrics_service import (
    get_indexed_documents_total,
    get_search_latency_p95_ms,
    get_search_samples_count,
    record_search_latency_ms,
)
from app.services.opensearch_client import get_opensearch_client
from app.services.search_service import search_docs
from app.services.storage_service import get_admin_audit_events, save_admin_audit_event, save_ai_feedback


router = APIRouter(tags=["api"])
logger = logging.getLogger("app.api")


def _extract_bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise HTTPException(status_code=401, detail="Authorization header is required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")
    return token.strip()


def require_authenticated_principal(authorization: str | None = Header(default=None)) -> TokenPrincipal:
    token = _extract_bearer_token(authorization)
    principal = get_token_principal(token)
    if principal is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return principal


def require_admin_principal(principal: TokenPrincipal = Depends(require_authenticated_principal)) -> TokenPrincipal:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return principal


@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, client: OpenSearch = Depends(get_opensearch_client)) -> SearchResponse:
    started_at = time.perf_counter()
    result = search_docs(client=client, payload=payload)
    latency_ms = (time.perf_counter() - started_at) * 1000.0
    record_search_latency_ms(latency_ms)
    logger.info(
        "search_request query=%r page=%s size=%s total_hits=%s latency_ms=%.2f",
        payload.query,
        payload.page,
        payload.size,
        result.total,
        latency_ms,
    )
    return result


@router.post("/documents/index/bootstrap", response_model=IndexBootstrapResponse)
def bootstrap_documents_index(client: OpenSearch = Depends(get_opensearch_client)) -> IndexBootstrapResponse:
    return bootstrap_index(client)


@router.post("/documents/upload", response_model=DocumentUploadResponse)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    product: str | None = Form(default=None),
    source_path: str | None = Form(default=None),
    language: str | None = Form(default=None),
    vendor: str | None = Form(default=None),
    domain: str | None = Form(default=None),
    release: str | None = Form(default=None),
    node_type: str | None = Form(default=None),
    interface: str | None = Form(default=None),
    protocol: str | None = Form(default=None),
    client: OpenSearch = Depends(get_opensearch_client),
) -> DocumentUploadResponse:
    try:
        return ingest_document(
            client=client,
            file=file,
            title=title,
            product=product,
            source_path=source_path,
            language=language,
            vendor=vendor,
            domain=domain,
            release=release,
            node_type=node_type,
            interface=interface,
            protocol=protocol,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/documents/package-gotd")
def package_gotd(
    files: list[UploadFile] = File(...),
    library_name: str = Form(...),
    product: str | None = Form(default=None),
    vendor: str | None = Form(default=None),
    domain: str | None = Form(default=None),
    release: str | None = Form(default=None),
    node_type: str | None = Form(default=None),
    interface: str | None = Form(default=None),
    protocol: str | None = Form(default=None),
    language: str | None = Form(default=None),
) -> Response:
    archive_bytes = create_gotd_archive(
        files=files,
        library_name=library_name,
        product=product,
        vendor=vendor,
        domain=domain,
        release=release,
        node_type=node_type,
        interface=interface,
        protocol=protocol,
        language=language,
    )
    file_name = f"{library_name}.gotd"
    return Response(
        content=archive_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/documents/tree", response_model=DocumentTreeResponse)
def read_document_tree() -> DocumentTreeResponse:
    return get_document_tree()


@router.get("/documents/{doc_id}", response_model=DocumentRecord)
def read_document(doc_id: str) -> DocumentRecord:
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("/ai/ask", response_model=AiAskResponse)
def ai_ask(payload: AiAskRequest, client: OpenSearch = Depends(get_opensearch_client)) -> AiAskResponse:
    started_at = time.perf_counter()
    result = ask_ai(payload, client)
    latency_ms = (time.perf_counter() - started_at) * 1000.0
    logger.info(
        "ai_request mode=%s question_len=%s citations=%s confidence=%.2f blocked=%s trace_id=%s context_doc_ids=%s latency_ms=%.2f",
        payload.mode,
        len(payload.question),
        len(result.citations),
        result.confidence,
        result.blocked,
        result.trace_id,
        len(payload.context_doc_ids),
        latency_ms,
    )
    return result


@router.post("/ai/feedback", response_model=AiFeedbackResponse)
def ai_feedback(payload: AiFeedbackRequest) -> AiFeedbackResponse:
    feedback_id = save_ai_feedback(trace_id=payload.trace_id, vote=payload.vote, reason=payload.reason)
    logger.info(
        "ai_feedback trace_id=%s vote=%s reason_len=%s",
        payload.trace_id,
        payload.vote,
        len(payload.reason or ""),
    )
    return AiFeedbackResponse(
        saved=True,
        feedback_id=feedback_id,
        trace_id=payload.trace_id,
        vote=payload.vote,
    )


@router.get("/metrics/kpi", response_model=KpiResponse)
def metrics_kpi() -> KpiResponse:
    return KpiResponse(
        indexed_documents_total=get_indexed_documents_total(),
        search_latency_p95_ms=get_search_latency_p95_ms(),
        search_samples=get_search_samples_count(),
    )


@router.post("/auth/login/password", response_model=AuthSuccessResponse)
def auth_login_password(payload: PasswordLoginRequest) -> AuthSuccessResponse:
    try:
        return login_with_password(payload)
    except AuthLockedError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/auth/sms/send-code", response_model=SmsSendResponse)
def auth_send_sms_code(payload: SmsSendRequest) -> SmsSendResponse:
    return send_sms_code(payload)


@router.post("/auth/sms/verify", response_model=AuthSuccessResponse)
def auth_verify_sms(payload: SmsVerifyRequest) -> AuthSuccessResponse:
    try:
        return verify_sms_code(payload)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/auth/qr/create", response_model=QrCreateResponse)
def auth_create_qr() -> QrCreateResponse:
    return create_qr_session()


@router.get("/auth/qr/status/{session_id}", response_model=QrStatusResponse)
def auth_qr_status(session_id: str) -> QrStatusResponse:
    try:
        return check_qr_status(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/auth/qr/confirm", response_model=AuthSuccessResponse)
def auth_qr_confirm(payload: QrConfirmRequest) -> AuthSuccessResponse:
    try:
        return confirm_qr_session(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/auth/register/validate", response_model=RegistrationValidateResponse)
def auth_register_validate(payload: RegistrationValidateRequest) -> RegistrationValidateResponse:
    return validate_registration(payload)


@router.post("/auth/register/start", response_model=RegistrationStartResponse)
def auth_register_start(payload: RegistrationStartRequest) -> RegistrationStartResponse:
    try:
        return start_registration(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/auth/register/confirm", response_model=AuthSuccessResponse)
def auth_register_confirm(payload: RegistrationConfirmRequest) -> AuthSuccessResponse:
    try:
        return confirm_registration(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/admin/users", response_model=list[AdminUserRecord])
def admin_list_users(_: TokenPrincipal = Depends(require_admin_principal)) -> list[AdminUserRecord]:
    users = list_registered_users()
    return [AdminUserRecord(**user.__dict__) for user in users]


@router.post("/admin/users", response_model=AdminUserRecord)
def admin_create_user(
    payload: AdminUserCreateRequest,
    principal: TokenPrincipal = Depends(require_admin_principal),
) -> AdminUserRecord:
    try:
        user = create_user(
            login=payload.login,
            password=payload.password,
            role=payload.role,
            phone=payload.phone,
            email=payload.email,
            display_name=payload.display_name,
        )
        save_admin_audit_event(
            actor_login=principal.login,
            actor_role=principal.role,
            action="admin.user.create",
            target=user.login,
            status="success",
            details={"role": user.role},
        )
        return AdminUserRecord(**user.__dict__)
    except ValueError as exc:
        save_admin_audit_event(
            actor_login=principal.login,
            actor_role=principal.role,
            action="admin.user.create",
            target=payload.login,
            status="failed",
            details={"error": str(exc)},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/admin/users/{login}", response_model=AdminUserRecord)
def admin_update_user(
    login: str,
    payload: AdminUserUpdateRequest,
    principal: TokenPrincipal = Depends(require_admin_principal),
) -> AdminUserRecord:
    try:
        update_kwargs: dict = {"unlock": payload.unlock}
        if payload.password is not None:
            update_kwargs["password"] = payload.password
        if payload.role is not None:
            update_kwargs["role"] = payload.role
        if payload.clear_phone:
            update_kwargs["phone"] = None
        elif payload.phone is not None:
            update_kwargs["phone"] = payload.phone
        if payload.clear_email:
            update_kwargs["email"] = None
        elif payload.email is not None:
            update_kwargs["email"] = payload.email
        if payload.clear_display_name:
            update_kwargs["display_name"] = None
        elif payload.display_name is not None:
            update_kwargs["display_name"] = payload.display_name

        user = update_user(login=login, **update_kwargs)
        save_admin_audit_event(
            actor_login=principal.login,
            actor_role=principal.role,
            action="admin.user.update",
            target=login,
            status="success",
            details={"role": user.role, "unlock": payload.unlock},
        )
        return AdminUserRecord(**user.__dict__)
    except ValueError as exc:
        save_admin_audit_event(
            actor_login=principal.login,
            actor_role=principal.role,
            action="admin.user.update",
            target=login,
            status="failed",
            details={"error": str(exc)},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/admin/users/{login}", response_model=AdminUserDeleteResponse)
def admin_delete_user(
    login: str,
    principal: TokenPrincipal = Depends(require_admin_principal),
) -> AdminUserDeleteResponse:
    try:
        deleted = delete_user(login)
        save_admin_audit_event(
            actor_login=principal.login,
            actor_role=principal.role,
            action="admin.user.delete",
            target=login,
            status="success" if deleted else "noop",
            details={"deleted": deleted},
        )
        return AdminUserDeleteResponse(deleted=deleted, login=login)
    except ValueError as exc:
        save_admin_audit_event(
            actor_login=principal.login,
            actor_role=principal.role,
            action="admin.user.delete",
            target=login,
            status="failed",
            details={"error": str(exc)},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/admin/audit")
def admin_read_audit_log(
    limit: int = 100,
    _: TokenPrincipal = Depends(require_admin_principal),
) -> list[dict]:
    return get_admin_audit_events(limit=limit)
