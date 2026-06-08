from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from io import BytesIO
from pathlib import Path
import re
import time
import uuid
import zipfile

from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from fastapi import UploadFile
from pypdf import PdfReader
from opensearchpy import OpenSearch

from app.config import settings
from app.schemas import (
    DocumentChunkRecord,
    DocumentMetadata,
    DocumentRecord,
    DocumentUploadResponse,
    IndexBootstrapResponse,
)
from app.services.metrics_service import record_stage_timing
from app.services.storage_service import get_document as get_stored_document
from app.services.storage_service import get_document_tree as get_stored_document_tree
from app.services.storage_service import get_idempotent_upload_result
from app.services.storage_service import save_idempotent_upload_result
from app.services.storage_service import save_document


INDEX_MAPPING = {
    "settings": {
        "index": {"number_of_shards": 1, "number_of_replicas": 0},
    },
    "mappings": {
        "properties": {
            "doc_id": {"type": "keyword"},
            "chunk_id": {"type": "keyword"},
            "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "content": {"type": "text"},
            "product": {"type": "keyword"},
            "vendor": {"type": "keyword"},
            "domain": {"type": "keyword"},
            "release": {"type": "keyword"},
            "node_type": {"type": "keyword"},
            "interface": {"type": "keyword"},
            "protocol": {"type": "keyword"},
            "source_format": {"type": "keyword"},
            "source_path": {"type": "keyword"},
            "language": {"type": "keyword"},
        }
    },
}

_INDEX_RETRY_MAX_ATTEMPTS = 3
_INDEX_RETRY_BASE_DELAY_SECONDS = 0.2

def bootstrap_index(client: OpenSearch) -> IndexBootstrapResponse:
    created = False
    if not client.indices.exists(index=settings.opensearch_index):
        client.indices.create(index=settings.opensearch_index, body=INDEX_MAPPING)
        created = True
    return IndexBootstrapResponse(index_name=settings.opensearch_index, created=created)


def _detect_source_format(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix or "txt"


def _extract_text_from_file(filename: str, content: bytes) -> str:
    started_at = time.perf_counter()
    source_format = _detect_source_format(filename)

    if source_format == "pdf":
        reader = PdfReader(BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        result = "\n".join(pages)
        record_stage_timing("upload.parse.pdf", (time.perf_counter() - started_at) * 1000.0)
        return result

    if source_format in {"docx", "doc"}:
        try:
            document = DocxDocument(BytesIO(content))
            result = "\n".join(paragraph.text for paragraph in document.paragraphs)
            record_stage_timing("upload.parse.docx", (time.perf_counter() - started_at) * 1000.0)
            return result
        except Exception:
            # Legacy .doc is not natively supported by python-docx; fallback to plain decode.
            result = content.decode("utf-8", errors="ignore")
            record_stage_timing("upload.parse.doc-fallback", (time.perf_counter() - started_at) * 1000.0)
            return result

    if source_format in {"html", "htm"}:
        soup = BeautifulSoup(content, "lxml")
        result = soup.get_text("\n")
        record_stage_timing("upload.parse.html", (time.perf_counter() - started_at) * 1000.0)
        return result

    result = content.decode("utf-8", errors="ignore")
    record_stage_timing("upload.parse.text", (time.perf_counter() - started_at) * 1000.0)
    return result


def _normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[\t\f\v]+", " ", normalized)
    normalized = re.sub(r"[ ]{2,}", " ", normalized)
    normalized = re.sub(r"\n[ ]+", "\n", normalized)
    return re.sub(r"\n{3,}", "\n\n", normalized).strip()


def _normalize_metadata_value(value: str | None, *, uppercase: bool = False, lowercase: bool = False) -> str | None:
    if value is None:
        return None

    normalized = re.sub(r"\s+", " ", value).strip()
    if not normalized:
        return None
    if uppercase:
        return normalized.upper()
    if lowercase:
        return normalized.lower()
    return normalized


def _normalize_title(value: str | None) -> str:
    normalized = _normalize_metadata_value(value)
    return normalized or "Untitled document"


def _derive_title(text: str, fallback: str) -> str:
    for line in _normalize_text(text).split("\n"):
        candidate = line.strip()
        if candidate:
            return candidate[:200]
    return _normalize_title(fallback)


def _chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:
    started_at = time.perf_counter()
    if not text:
        return []

    normalized = _normalize_text(text)
    paragraphs = [paragraph.strip() for paragraph in normalized.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current_chunk = ""

    for paragraph in paragraphs:
        candidate = paragraph if not current_chunk else f"{current_chunk}\n\n{paragraph}"
        if len(candidate) <= chunk_size:
            current_chunk = candidate
            continue

        if current_chunk:
            chunks.append(current_chunk.strip())

        if len(paragraph) <= chunk_size:
            current_chunk = paragraph
            continue

        start = 0
        while start < len(paragraph):
            end = min(start + chunk_size, len(paragraph))
            segment = paragraph[start:end].strip()
            if segment:
                chunks.append(segment)
            if end >= len(paragraph):
                break
            start = max(end - overlap, start + 1)
        current_chunk = ""

    if current_chunk:
        chunks.append(current_chunk.strip())

    record_stage_timing("upload.chunking", (time.perf_counter() - started_at) * 1000.0)
    return chunks


def _build_chunk_records(
    doc_id: str,
    source_format: str,
    chunks: list[str],
    metadata: DocumentMetadata,
) -> list[DocumentChunkRecord]:
    records: list[DocumentChunkRecord] = []
    for index, chunk in enumerate(chunks, start=1):
        chunk_id = f"{doc_id}-{index:04d}"
        records.append(
            DocumentChunkRecord(
                doc_id=doc_id,
                chunk_id=chunk_id,
                title=metadata.title,
                content=chunk,
                vendor=metadata.vendor,
                domain=metadata.domain,
                release=metadata.release,
                node_type=metadata.node_type,
                interface=metadata.interface,
                protocol=metadata.protocol,
                source_format=source_format,
                source_path=metadata.source_path,
                language=metadata.language,
            )
        )
    return records


def _index_and_store_document(
    client: OpenSearch,
    source_format: str,
    metadata: DocumentMetadata,
    chunks: list[str],
) -> tuple[str, int]:
    started_at = time.perf_counter()
    doc_id = str(uuid.uuid4())
    chunk_records = _build_chunk_records(doc_id=doc_id, source_format=source_format, chunks=chunks, metadata=metadata)

    bulk_actions: list[dict] = []
    for chunk_record in chunk_records:
        bulk_actions.append({"index": {"_index": settings.opensearch_index, "_id": chunk_record.chunk_id}})
        bulk_actions.append({**chunk_record.model_dump(), "product": metadata.product})

    if bulk_actions:
        _bulk_index_with_retry(client=client, bulk_actions=bulk_actions)

    document_record = DocumentRecord(
        doc_id=doc_id,
        title=metadata.title,
        source_format=source_format,
        metadata=metadata,
        chunk_count=len(chunk_records),
        chunks=chunk_records,
    )
    save_document(document_record)
    record_stage_timing("upload.index-and-store", (time.perf_counter() - started_at) * 1000.0)
    return doc_id, len(chunk_records)


def _bulk_index_with_retry(*, client: OpenSearch, bulk_actions: list[dict]) -> None:
    last_error: Exception | None = None
    for attempt in range(1, _INDEX_RETRY_MAX_ATTEMPTS + 1):
        try:
            started_at = time.perf_counter()
            client.bulk(body=bulk_actions, refresh=True)
            record_stage_timing("upload.bulk-index.attempt", (time.perf_counter() - started_at) * 1000.0)
            return
        except Exception as exc:  # pragma: no cover - covered by integration behavior
            last_error = exc
            if attempt >= _INDEX_RETRY_MAX_ATTEMPTS:
                break
            time.sleep(_INDEX_RETRY_BASE_DELAY_SECONDS * attempt)
    raise RuntimeError("Индексация чанков завершилась неуспешно после повторов") from last_error


def _build_upload_request_key(
    *,
    filename: str,
    raw_content: bytes,
    title: str,
    product: str | None,
    source_path: str | None,
    language: str | None,
    vendor: str | None,
    domain: str | None,
    release: str | None,
    node_type: str | None,
    interface: str | None,
    protocol: str | None,
    idempotency_key: str | None,
) -> str:
    normalized_idempotency_key = (idempotency_key or "").strip()
    if normalized_idempotency_key:
        return f"custom:{normalized_idempotency_key}"

    descriptor = {
        "filename": filename,
        "title": title,
        "product": product,
        "source_path": source_path,
        "language": language,
        "vendor": vendor,
        "domain": domain,
        "release": release,
        "node_type": node_type,
        "interface": interface,
        "protocol": protocol,
        "content_sha256": hashlib.sha256(raw_content).hexdigest(),
    }
    digest = hashlib.sha256(json.dumps(descriptor, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return f"auto:{digest}"


def _ingest_single_from_bytes(
    client: OpenSearch,
    *,
    filename: str,
    raw_content: bytes,
    title: str,
    product: str | None,
    source_path: str | None,
    language: str | None,
    vendor: str | None,
    domain: str | None,
    release: str | None,
    node_type: str | None,
    interface: str | None,
    protocol: str | None,
) -> tuple[str, int, str, DocumentMetadata]:
    source_format = _detect_source_format(filename)
    extracted_text = _extract_text_from_file(filename, raw_content)
    chunks = _chunk_text(extracted_text)

    resolved_title = _normalize_title(title)
    if resolved_title == "Untitled document":
        resolved_title = _derive_title(extracted_text, filename)

    metadata = _build_document_metadata(
        title=resolved_title,
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

    if not chunks and extracted_text:
        chunks = [_normalize_text(extracted_text)]

    doc_id, chunks_count = _index_and_store_document(
        client=client,
        source_format=source_format,
        metadata=metadata,
        chunks=chunks,
    )
    return doc_id, chunks_count, source_format, metadata


def _safe_archive_name(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return sanitized or "document"


def create_gotd_archive(
    *,
    files: list[UploadFile],
    library_name: str,
    product: str | None = None,
    vendor: str | None = None,
    domain: str | None = None,
    release: str | None = None,
    node_type: str | None = None,
    interface: str | None = None,
    protocol: str | None = None,
    language: str | None = None,
) -> bytes:
    used_names: set[str] = set()
    manifest_documents: list[dict] = []
    archive_payloads: list[tuple[str, bytes]] = []

    for upload in files:
        original_name = upload.filename or "document.txt"
        base_name = _safe_archive_name(Path(original_name).name)
        archive_name = base_name
        suffix = 1
        while archive_name.lower() in used_names:
            candidate = Path(base_name)
            archive_name = f"{candidate.stem}_{suffix}{candidate.suffix}"
            suffix += 1
        used_names.add(archive_name.lower())

        content = upload.file.read()
        archive_payloads.append((f"files/{archive_name}", content))
        manifest_documents.append(
            {
                "filename": archive_name,
                "title": Path(archive_name).stem,
                "product": product,
                "vendor": vendor,
                "domain": domain,
                "release": release,
                "node_type": node_type,
                "interface": interface,
                "protocol": protocol,
                "language": language,
            }
        )

    manifest = {
        "format": "gotd",
        "version": "1.0",
        "library_name": _normalize_title(library_name),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "documents": manifest_documents,
    }

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for archive_path, content in archive_payloads:
            archive.writestr(archive_path, content)

    return buffer.getvalue()


def _read_gotd_manifest(archive: zipfile.ZipFile) -> dict:
    try:
        with archive.open("manifest.json") as manifest_file:
            return json.loads(manifest_file.read().decode("utf-8", errors="ignore"))
    except KeyError:
        return {}


def _manifest_lookup(manifest: dict) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for item in manifest.get("documents", []):
        filename = item.get("filename")
        if filename:
            lookup[Path(filename).name.lower()] = item
    return lookup


def _collect_archive_file_names(archive: zipfile.ZipFile) -> list[str]:
    return [
        name
        for name in archive.namelist()
        if not name.endswith("/") and name != "manifest.json" and not name.startswith("__MACOSX/")
    ]


def ingest_gotd_library(
    client: OpenSearch,
    *,
    archive_bytes: bytes,
    title: str,
    product: str | None,
    source_path: str | None,
    language: str | None,
    vendor: str | None,
    domain: str | None,
    release: str | None,
    node_type: str | None,
    interface: str | None,
    protocol: str | None,
) -> DocumentUploadResponse:
    try:
        archive = zipfile.ZipFile(BytesIO(archive_bytes), mode="r")
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid .gotd archive") from exc

    with archive:
        manifest = _read_gotd_manifest(archive)
        manifest_by_filename = _manifest_lookup(manifest)
        file_names = _collect_archive_file_names(archive)

        ingested_document_ids: list[str] = []
        chunks_total = 0
        for internal_name in file_names:
            filename_only = Path(internal_name).name
            entry = manifest_by_filename.get(filename_only.lower(), {})
            raw_content = archive.read(internal_name)

            doc_id, chunk_count, _, _ = _ingest_single_from_bytes(
                client=client,
                filename=filename_only,
                raw_content=raw_content,
                title=entry.get("title") or Path(filename_only).stem,
                product=entry.get("product") or product,
                source_path=entry.get("source_path") or f"gotd:{filename_only}",
                language=entry.get("language") or language,
                vendor=entry.get("vendor") or vendor,
                domain=entry.get("domain") or domain,
                release=entry.get("release") or release,
                node_type=entry.get("node_type") or node_type,
                interface=entry.get("interface") or interface,
                protocol=entry.get("protocol") or protocol,
            )
            ingested_document_ids.append(doc_id)
            chunks_total += chunk_count

    library_title = _normalize_title(manifest.get("library_name") if isinstance(manifest, dict) else None)
    if library_title == "Untitled document":
        library_title = _normalize_title(title)

    return DocumentUploadResponse(
        doc_id=str(uuid.uuid4()),
        title=library_title,
        chunks_indexed=chunks_total,
        source_format="gotd",
        library_items=len(ingested_document_ids),
        ingested_document_ids=ingested_document_ids,
    )


def _build_document_metadata(
    title: str,
    product: str | None,
    source_path: str | None,
    language: str | None,
    vendor: str | None,
    domain: str | None,
    release: str | None,
    node_type: str | None,
    interface: str | None,
    protocol: str | None,
) -> DocumentMetadata:
    return DocumentMetadata(
        title=_normalize_title(title),
        product=_normalize_metadata_value(product),
        source_path=_normalize_metadata_value(source_path),
        language=_normalize_metadata_value(language, lowercase=True),
        vendor=_normalize_metadata_value(vendor),
        domain=_normalize_metadata_value(domain, lowercase=True),
        release=_normalize_metadata_value(release, uppercase=True),
        node_type=_normalize_metadata_value(node_type, uppercase=True),
        interface=_normalize_metadata_value(interface, uppercase=True),
        protocol=_normalize_metadata_value(protocol, uppercase=True),
    )


def ingest_document(
    client: OpenSearch,
    file: UploadFile,
    title: str,
    product: str | None = None,
    source_path: str | None = None,
    language: str | None = None,
    vendor: str | None = None,
    domain: str | None = None,
    release: str | None = None,
    node_type: str | None = None,
    interface: str | None = None,
    protocol: str | None = None,
    idempotency_key: str | None = None,
) -> DocumentUploadResponse:
    raw_content = file.file.read()
    filename = file.filename or title
    request_key = _build_upload_request_key(
        filename=filename,
        raw_content=raw_content,
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
        idempotency_key=idempotency_key,
    )

    existing = get_idempotent_upload_result(request_key)
    if existing is not None:
        return existing

    source_format = _detect_source_format(filename)

    if source_format == "gotd":
        response = ingest_gotd_library(
            client=client,
            archive_bytes=raw_content,
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
        response.idempotency_key = request_key
        response.idempotent_replay = False
        save_idempotent_upload_result(request_key, response)
        return response

    doc_id, chunks_count, source_format, metadata = _ingest_single_from_bytes(
        client=client,
        filename=filename,
        raw_content=raw_content,
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

    response = DocumentUploadResponse(
        doc_id=doc_id,
        title=metadata.title,
        chunks_indexed=chunks_count,
        source_format=source_format,
        idempotency_key=request_key,
        idempotent_replay=False,
    )
    save_idempotent_upload_result(request_key, response)
    return response


def get_document(doc_id: str) -> DocumentRecord | None:
    return get_stored_document(doc_id)


def get_document_tree():
    return get_stored_document_tree()
