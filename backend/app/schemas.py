from pydantic import BaseModel, Field
from typing import Literal


class SearchFilters(BaseModel):
    product: list[str] = Field(default_factory=list)
    vendor: list[str] = Field(default_factory=list)
    domain: list[str] = Field(default_factory=list)
    release: list[str] = Field(default_factory=list)
    node_type: list[str] = Field(default_factory=list)
    interface: list[str] = Field(default_factory=list)
    protocol: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    filters: SearchFilters = Field(default_factory=SearchFilters)


class SearchHit(BaseModel):
    doc_id: str
    chunk_id: str
    title: str
    snippet: str
    score: float
    vendor: str | None = None
    domain: str | None = None
    release: str | None = None
    node_type: str | None = None
    interface: str | None = None
    protocol: str | None = None


class SearchResponse(BaseModel):
    total: int
    page: int
    size: int
    hits: list[SearchHit]
    facets: dict[str, list[dict]]


class AiAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    context_doc_ids: list[str] = Field(default_factory=list)
    max_citations: int = Field(default=5, ge=1, le=20)
    mode: Literal["explain", "compare", "diagnose"] = "explain"


class AiCitation(BaseModel):
    doc_id: str
    chunk_id: str
    title: str
    snippet: str


class AiAskResponse(BaseModel):
    answer: str
    confidence: float
    citations: list[AiCitation]
    source_policy: str = "strict-required-citations"
    blocked: bool = False
    trace_id: str
    retrieval_stats: dict[str, int] = Field(default_factory=dict)


class AiFeedbackRequest(BaseModel):
    trace_id: str = Field(min_length=8, max_length=120)
    vote: Literal["like", "dislike"]
    reason: str | None = Field(default=None, max_length=500)


class AiFeedbackResponse(BaseModel):
    saved: bool
    feedback_id: str
    trace_id: str
    vote: Literal["like", "dislike"]


class DocumentMetadata(BaseModel):
    title: str = Field(default="Untitled document")
    product: str | None = None
    vendor: str | None = None
    domain: str | None = None
    release: str | None = None
    node_type: str | None = None
    interface: str | None = None
    protocol: str | None = None
    source_path: str | None = None
    language: str | None = None


class DocumentUploadResponse(BaseModel):
    doc_id: str
    title: str
    chunks_indexed: int
    source_format: str
    library_items: int | None = None
    ingested_document_ids: list[str] | None = None


class IndexBootstrapResponse(BaseModel):
    index_name: str
    created: bool


class DocumentChunkRecord(BaseModel):
    doc_id: str
    chunk_id: str
    title: str
    content: str
    score: float = 0.0
    vendor: str | None = None
    domain: str | None = None
    release: str | None = None
    node_type: str | None = None
    interface: str | None = None
    protocol: str | None = None
    source_format: str | None = None
    source_path: str | None = None
    language: str | None = None


class DocumentRecord(BaseModel):
    doc_id: str
    title: str
    source_format: str
    metadata: DocumentMetadata
    chunk_count: int
    chunks: list[DocumentChunkRecord]


class DocumentTreeTopic(BaseModel):
    doc_id: str
    title: str
    vendor: str | None = None
    release: str | None = None
    node_type: str | None = None


class DocumentTreeDomain(BaseModel):
    name: str
    topics: list[DocumentTreeTopic]


class DocumentTreeRelease(BaseModel):
    name: str
    domains: list[DocumentTreeDomain]


class DocumentTreeProduct(BaseModel):
    name: str
    releases: list[DocumentTreeRelease]


class DocumentTreeResponse(BaseModel):
    products: list[DocumentTreeProduct]


class PasswordLoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class SmsSendRequest(BaseModel):
    phone: str = Field(min_length=5, max_length=32)


class SmsSendResponse(BaseModel):
    success: bool
    phone_masked: str
    expires_in: int
    demo_code: str | None = None


class SmsVerifyRequest(BaseModel):
    phone: str = Field(min_length=5, max_length=32)
    code: str = Field(min_length=4, max_length=12)


class QrCreateResponse(BaseModel):
    session_id: str
    qr_payload: str
    qr_image_data_url: str
    expires_in: int


class QrStatusResponse(BaseModel):
    session_id: str
    status: str
    access_token: str | None = None
    expires_in: int


class QrConfirmRequest(BaseModel):
    session_id: str


class AuthSuccessResponse(BaseModel):
    success: bool
    method: str
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    display_name: str | None = None
    role: Literal["admin", "user"] = "user"


class AdminUserRecord(BaseModel):
    login: str
    display_name: str | None
    role: Literal["admin", "user"]
    phone: str | None
    email: str | None
    failed_attempts: int
    total_failed_attempts: int
    locked_until: str | None
    created_at: str


class AdminUserCreateRequest(BaseModel):
    login: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=200)
    role: Literal["admin", "user"] = "user"
    phone: str | None = Field(default=None, min_length=5, max_length=32)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    display_name: str | None = Field(default=None, max_length=120)


class AdminUserUpdateRequest(BaseModel):
    password: str | None = Field(default=None, min_length=8, max_length=200)
    role: Literal["admin", "user"] | None = None
    phone: str | None = Field(default=None, min_length=5, max_length=32)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    display_name: str | None = Field(default=None, max_length=120)
    clear_phone: bool = False
    clear_email: bool = False
    clear_display_name: bool = False
    unlock: bool = False


class AdminUserDeleteResponse(BaseModel):
    deleted: bool
    login: str


class RegistrationValidateRequest(BaseModel):
    login: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, min_length=5, max_length=32)
    email: str | None = Field(default=None, min_length=5, max_length=255)


class RegistrationValidateResponse(BaseModel):
    valid: bool
    login_available: bool
    errors: list[str] = Field(default_factory=list)


class RegistrationStartRequest(BaseModel):
    login: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, min_length=5, max_length=32)
    email: str | None = Field(default=None, min_length=5, max_length=255)


class RegistrationStartResponse(BaseModel):
    challenge_id: str
    contact_masked: str
    expires_in: int
    demo_code: str | None = None


class RegistrationConfirmRequest(BaseModel):
    challenge_id: str
    code: str = Field(min_length=4, max_length=12)


class KpiResponse(BaseModel):
    indexed_documents_total: int
    search_latency_p95_ms: float
    search_samples: int
