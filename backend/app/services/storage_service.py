from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from app.config import settings
from app.schemas import (
    AiAuditRecord,
    DocumentChunkRecord,
    DocumentMetadata,
    DocumentRecord,
    DocumentUploadResponse,
    DocumentTreeDomain,
    DocumentTreeProduct,
    DocumentTreeRelease,
    DocumentTreeResponse,
    DocumentTreeTopic,
)


def _get_connection() -> sqlite3.Connection:
    db_path = Path(settings.storage_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_storage() -> None:
    with _get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source_format TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                chunk_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS document_chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                vendor TEXT,
                domain TEXT,
                release TEXT,
                node_type TEXT,
                interface TEXT,
                protocol TEXT,
                source_format TEXT,
                source_path TEXT,
                language TEXT,
                score REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_document_chunks_doc_id ON document_chunks(doc_id);

            CREATE TABLE IF NOT EXISTS ai_feedback (
                feedback_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                vote TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_ai_feedback_trace_id ON ai_feedback(trace_id);

            CREATE TABLE IF NOT EXISTS admin_audit_log (
                audit_id TEXT PRIMARY KEY,
                actor_login TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT,
                status TEXT NOT NULL,
                details_json TEXT,
                trace_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_admin_audit_created_at ON admin_audit_log(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_admin_audit_actor ON admin_audit_log(actor_login);

            CREATE TABLE IF NOT EXISTS ai_answer_audit_log (
                audit_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                question TEXT NOT NULL,
                blocked INTEGER NOT NULL,
                confidence REAL NOT NULL,
                citations_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_ai_answer_audit_trace ON ai_answer_audit_log(trace_id);
            CREATE INDEX IF NOT EXISTS idx_ai_answer_audit_created ON ai_answer_audit_log(created_at DESC);

            CREATE TABLE IF NOT EXISTS ingestion_idempotency (
                request_key TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def save_document(record: DocumentRecord) -> None:
    with _get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO documents (doc_id, title, source_format, metadata_json, chunk_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.doc_id,
                record.title,
                record.source_format,
                json.dumps(record.metadata.model_dump(), ensure_ascii=False),
                record.chunk_count,
            ),
        )
        connection.execute("DELETE FROM document_chunks WHERE doc_id = ?", (record.doc_id,))
        connection.executemany(
            """
            INSERT INTO document_chunks (
                chunk_id, doc_id, title, content, vendor, domain, release,
                node_type, interface, protocol, source_format, source_path,
                language, score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    chunk.chunk_id,
                    record.doc_id,
                    chunk.title,
                    chunk.content,
                    chunk.vendor,
                    chunk.domain,
                    chunk.release,
                    chunk.node_type,
                    chunk.interface,
                    chunk.protocol,
                    chunk.source_format,
                    chunk.source_path,
                    chunk.language,
                    chunk.score,
                )
                for chunk in record.chunks
            ],
        )


def get_document(doc_id: str) -> DocumentRecord | None:
    with _get_connection() as connection:
        document_row = connection.execute(
            "SELECT doc_id, title, source_format, metadata_json, chunk_count FROM documents WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()
        if document_row is None:
            return None

        chunk_rows = connection.execute(
            """
            SELECT chunk_id, doc_id, title, content, vendor, domain, release,
                   node_type, interface, protocol, source_format, source_path,
                   language, score
            FROM document_chunks
            WHERE doc_id = ?
            ORDER BY chunk_id
            """,
            (doc_id,),
        ).fetchall()

    metadata = DocumentMetadata(**json.loads(document_row["metadata_json"]))
    chunks = [DocumentChunkRecord(**dict(row)) for row in chunk_rows]

    return DocumentRecord(
        doc_id=document_row["doc_id"],
        title=document_row["title"],
        source_format=document_row["source_format"],
        metadata=metadata,
        chunk_count=document_row["chunk_count"],
        chunks=chunks,
    )


def get_document_tree() -> DocumentTreeResponse:
    with _get_connection() as connection:
        rows = connection.execute(
            "SELECT doc_id, title, metadata_json FROM documents ORDER BY title"
        ).fetchall()

    tree: dict[str, dict[str, dict[str, list[DocumentTreeTopic]]]] = {}
    for row in rows:
        metadata = DocumentMetadata(**json.loads(row["metadata_json"]))
        product = metadata.product or metadata.vendor or "Uncategorized"
        release = metadata.release or "UNSPECIFIED"
        domain = metadata.domain or "misc"

        topic = DocumentTreeTopic(
            doc_id=row["doc_id"],
            title=row["title"],
            vendor=metadata.vendor,
            release=metadata.release,
            node_type=metadata.node_type,
        )
        tree.setdefault(product, {}).setdefault(release, {}).setdefault(domain, []).append(topic)

    products: list[DocumentTreeProduct] = []
    for product_name in sorted(tree):
        releases: list[DocumentTreeRelease] = []
        for release_name in sorted(tree[product_name]):
            domains: list[DocumentTreeDomain] = []
            for domain_name in sorted(tree[product_name][release_name]):
                topics = sorted(tree[product_name][release_name][domain_name], key=lambda item: item.title.lower())
                domains.append(DocumentTreeDomain(name=domain_name, topics=topics))
            releases.append(DocumentTreeRelease(name=release_name, domains=domains))
        products.append(DocumentTreeProduct(name=product_name, releases=releases))

    return DocumentTreeResponse(products=products)


def count_documents() -> int:
    with _get_connection() as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM documents").fetchone()
    return int(row["total"] if row is not None else 0)


def save_ai_feedback(trace_id: str, vote: str, reason: str | None = None) -> str:
    feedback_id = str(uuid4())
    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO ai_feedback (feedback_id, trace_id, vote, reason)
            VALUES (?, ?, ?, ?)
            """,
            (feedback_id, trace_id, vote, reason),
        )
    return feedback_id


def get_ai_feedback_by_trace(trace_id: str) -> list[dict]:
    with _get_connection() as connection:
        rows = connection.execute(
            """
            SELECT feedback_id, trace_id, vote, reason, created_at
            FROM ai_feedback
            WHERE trace_id = ?
            ORDER BY created_at DESC
            """,
            (trace_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def save_admin_audit_event(
    *,
    actor_login: str,
    actor_role: str,
    action: str,
    target: str | None,
    status: str,
    details: dict | None = None,
    trace_id: str | None = None,
) -> str:
    audit_id = str(uuid4())
    details_json = json.dumps(details, ensure_ascii=False) if details is not None else None
    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO admin_audit_log (
                audit_id, actor_login, actor_role, action, target, status, details_json, trace_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (audit_id, actor_login, actor_role, action, target, status, details_json, trace_id),
        )
    return audit_id


def get_admin_audit_events(limit: int = 100) -> list[dict]:
    safe_limit = max(1, min(limit, 500))
    with _get_connection() as connection:
        rows = connection.execute(
            """
            SELECT audit_id, actor_login, actor_role, action, target, status, details_json, trace_id, created_at
            FROM admin_audit_log
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    result: list[dict] = []
    for row in rows:
        item = dict(row)
        if item.get("details_json"):
            try:
                item["details"] = json.loads(item["details_json"])
            except json.JSONDecodeError:
                item["details"] = None
        else:
            item["details"] = None
        result.append(item)
    return result


def save_ai_answer_audit_event(
    *,
    trace_id: str,
    mode: str,
    question: str,
    blocked: bool,
    confidence: float,
    citations_count: int,
    status: str,
    error_message: str | None = None,
) -> str:
    audit_id = str(uuid4())
    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO ai_answer_audit_log (
                audit_id, trace_id, mode, question, blocked, confidence, citations_count, status, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                trace_id,
                mode,
                question,
                1 if blocked else 0,
                confidence,
                citations_count,
                status,
                error_message,
            ),
        )
    return audit_id


def get_ai_answer_audit_events(limit: int = 100) -> list[AiAuditRecord]:
    safe_limit = max(1, min(limit, 500))
    with _get_connection() as connection:
        rows = connection.execute(
            """
            SELECT audit_id, trace_id, mode, question, blocked, confidence, citations_count, status, error_message, created_at
            FROM ai_answer_audit_log
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    return [
        AiAuditRecord(
            audit_id=row["audit_id"],
            trace_id=row["trace_id"],
            mode=row["mode"],
            question=row["question"],
            blocked=bool(row["blocked"]),
            confidence=float(row["confidence"]),
            citations_count=int(row["citations_count"]),
            status=row["status"],
            error_message=row["error_message"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_idempotent_upload_result(request_key: str) -> DocumentUploadResponse | None:
    with _get_connection() as connection:
        row = connection.execute(
            "SELECT response_json FROM ingestion_idempotency WHERE request_key = ?",
            (request_key,),
        ).fetchone()
    if row is None:
        return None
    payload = json.loads(row["response_json"])
    payload["idempotent_replay"] = True
    payload["idempotency_key"] = request_key
    return DocumentUploadResponse(**payload)


def save_idempotent_upload_result(request_key: str, response: DocumentUploadResponse) -> None:
    payload = response.model_dump()
    payload["idempotency_key"] = request_key
    payload["idempotent_replay"] = False
    serialized = json.dumps(payload, ensure_ascii=False)
    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO ingestion_idempotency(request_key, response_json, created_at, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(request_key)
            DO UPDATE SET response_json = excluded.response_json, updated_at = CURRENT_TIMESTAMP
            """,
            (request_key, serialized),
        )