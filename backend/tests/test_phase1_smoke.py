from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.auth_service import create_user, delete_user, list_registered_users, update_user
from app.services.opensearch_client import get_opensearch_client
from app.services.storage_service import get_admin_audit_events, get_ai_feedback_by_trace


class FakeIndices:
    def __init__(self, client: "FakeOpenSearch"):
        self._client = client

    def exists(self, index: str) -> bool:
        return index in self._client.indexes

    def create(self, index: str, body: dict) -> dict:
        self._client.indexes[index] = body
        return {"acknowledged": True}


class FakeOpenSearch:
    def __init__(self) -> None:
        self.indexes: dict[str, dict] = {}
        self.documents: dict[str, dict] = {}
        self.indices = FakeIndices(self)

    def bulk(self, body: list[dict], refresh: bool = False) -> dict:
        for offset in range(0, len(body), 2):
            action = body[offset]["index"]
            document = body[offset + 1]
            self.documents[action["_id"]] = document
        return {"errors": False}

    def search(self, index: str, body: dict) -> dict:
        query_text = body["query"]["bool"]["must"][0]["multi_match"]["query"].lower()
        filter_clauses = body["query"]["bool"].get("filter", [])

        matched_documents = []
        for document_id, document in self.documents.items():
            if not self._matches_filters(document, filter_clauses):
                continue

            haystack = f"{document.get('title', '')} {document.get('content', '')}".lower()
            if query_text in haystack:
                matched_documents.append((document_id, document))

        hits = []
        for document_id, document in matched_documents:
            content = document.get("content", "")
            highlight = self._highlight(content, query_text)
            hits.append(
                {
                    "_id": document_id,
                    "_score": float(content.lower().count(query_text) + 1),
                    "_source": document,
                    "highlight": {"content": [highlight]},
                }
            )

        return {
            "hits": {"total": {"value": len(hits)}, "hits": hits},
            "aggregations": self._build_aggregations([document for _, document in matched_documents]),
        }

    @staticmethod
    def _matches_filters(document: dict, filter_clauses: list[dict]) -> bool:
        for clause in filter_clauses:
            terms = clause["terms"]
            field_name, accepted_values = next(iter(terms.items()))
            field_name = field_name.replace(".keyword", "")
            if document.get(field_name) not in accepted_values:
                return False
        return True

    @staticmethod
    def _highlight(content: str, query_text: str) -> str:
        index = content.lower().find(query_text)
        if index < 0:
            return content[:240]
        end = index + len(query_text)
        return f"{content[:index]}<mark>{content[index:end]}</mark>{content[end:]}"

    @staticmethod
    def _build_aggregations(documents: list[dict]) -> dict:
        def bucketize(field_name: str) -> dict:
            counts: dict[str, int] = {}
            for document in documents:
                value = document.get(field_name)
                if value:
                    counts[value] = counts.get(value, 0) + 1
            return {
                "buckets": [
                    {"key": key, "doc_count": count}
                    for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
                ]
            }

        return {
            "products": bucketize("product"),
            "vendors": bucketize("vendor"),
            "domains": bucketize("domain"),
            "releases": bucketize("release"),
            "node_types": bucketize("node_type"),
            "interfaces": bucketize("interface"),
            "protocols": bucketize("protocol"),
        }


def _load_sample(name: str) -> bytes:
    sample_path = Path(__file__).resolve().parents[1] / "sample_docs" / name
    return sample_path.read_bytes()


def _set_test_db(tmp_path: Path) -> str:
    original_path = settings.storage_db_path
    settings.storage_db_path = str(tmp_path / "test-library.db")
    return original_path


def test_phase1_smoke_upload_search_and_retrieve(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        bootstrap_response = client.post("/api/v1/documents/index/bootstrap")
        assert bootstrap_response.status_code == 200
        assert bootstrap_response.json()["created"] is True

        upload_response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("sample_epc.txt", _load_sample("sample_epc.txt"), "text/plain")},
            data={
                "title": "Ericsson EPC Mobility Management Guide",
                "product": "Ericsson Packet Core",
                "vendor": "  Ericsson  ",
                "domain": " EPC ",
                "release": "r16",
                "node_type": "mme",
                "interface": "s1-mme",
                "protocol": "gtp-c",
                "language": "EN",
                "source_path": "sample_docs/sample_epc.txt",
            },
        )
        assert upload_response.status_code == 200
        upload_payload = upload_response.json()
        assert upload_payload["chunks_indexed"] >= 1

        document_response = client.get(f"/api/v1/documents/{upload_payload['doc_id']}")
        assert document_response.status_code == 200
        document_payload = document_response.json()
        assert document_payload["title"] == "Ericsson EPC Mobility Management Guide"
        assert document_payload["metadata"]["product"] == "Ericsson Packet Core"
        assert document_payload["metadata"]["vendor"] == "Ericsson"
        assert document_payload["metadata"]["domain"] == "epc"
        assert document_payload["metadata"]["release"] == "R16"
        assert document_payload["metadata"]["node_type"] == "MME"
        assert document_payload["metadata"]["interface"] == "S1-MME"
        assert document_payload["metadata"]["protocol"] == "GTP-C"
        assert document_payload["metadata"]["language"] == "en"

        search_response = client.post(
            "/api/v1/search",
            json={
                "query": "paging",
                "page": 1,
                "size": 10,
                "filters": {"product": ["Ericsson Packet Core"], "vendor": ["Ericsson"], "domain": ["epc"]},
            },
        )
        assert search_response.status_code == 200
        search_payload = search_response.json()
        assert search_payload["total"] >= 1
        assert search_payload["hits"][0]["title"] == "Ericsson EPC Mobility Management Guide"
        assert search_payload["facets"]["product"][0] == {"key": "Ericsson Packet Core", "count": 1}

    app.dependency_overrides.clear()
    settings.storage_db_path = original_db_path


def test_phase1_faceted_search_scenario(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        client.post("/api/v1/documents/index/bootstrap")

        client.post(
            "/api/v1/documents/upload",
            files={"file": ("sample_epc.txt", _load_sample("sample_epc.txt"), "text/plain")},
            data={
                "title": "Ericsson EPC Mobility Management Guide",
                "product": "Ericsson Packet Core",
                "vendor": "Ericsson",
                "domain": "epc",
                "release": "R16",
                "node_type": "MME",
                "interface": "S1-MME",
                "protocol": "GTP-C",
                "language": "en",
                "source_path": "sample_docs/sample_epc.txt",
            },
        )

        client.post(
            "/api/v1/documents/upload",
            files={"file": ("sample_5gc.html", _load_sample("sample_5gc.html"), "text/html")},
            data={
                "title": "Huawei 5GC Service-Based Architecture",
                "product": "Huawei 5GC",
                "vendor": "Huawei",
                "domain": "5gc",
                "release": "R17",
                "node_type": "AMF",
                "interface": "N2",
                "protocol": "HTTP/2",
                "language": "en",
                "source_path": "sample_docs/sample_5gc.html",
            },
        )

        search_response = client.post(
            "/api/v1/search",
            json={"query": "documentation", "page": 1, "size": 10, "filters": {}},
        )
        assert search_response.status_code == 200
        search_payload = search_response.json()
        assert search_payload["total"] == 2
        assert {bucket["key"] for bucket in search_payload["facets"]["product"]} == {"Ericsson Packet Core", "Huawei 5GC"}
        assert {bucket["key"] for bucket in search_payload["facets"]["vendor"]} == {"Ericsson", "Huawei"}
        assert {bucket["key"] for bucket in search_payload["facets"]["domain"]} == {"epc", "5gc"}
        assert all("count" in bucket for bucket in search_payload["facets"]["vendor"])

        filtered_response = client.post(
            "/api/v1/search",
            json={
                "query": "documentation",
                "page": 1,
                "size": 10,
                "filters": {"vendor": ["Huawei"]},
            },
        )
        assert filtered_response.status_code == 200
        filtered_payload = filtered_response.json()
        assert filtered_payload["total"] == 1
        assert filtered_payload["hits"][0]["title"] == "Huawei 5GC Service-Based Architecture"
        assert filtered_payload["facets"]["vendor"][0] == {"key": "Huawei", "count": 1}

        tree_response = client.get("/api/v1/documents/tree")
        assert tree_response.status_code == 200
        tree_payload = tree_response.json()
        assert {product["name"] for product in tree_payload["products"]} == {"Ericsson Packet Core", "Huawei 5GC"}

        ericsson_product = next(product for product in tree_payload["products"] if product["name"] == "Ericsson Packet Core")
        assert ericsson_product["releases"][0]["name"] == "R16"
        assert ericsson_product["releases"][0]["domains"][0]["name"] == "epc"
        assert ericsson_product["releases"][0]["domains"][0]["topics"][0]["title"] == "Ericsson EPC Mobility Management Guide"

    app.dependency_overrides.clear()
    settings.storage_db_path = original_db_path


def test_gotd_pack_and_ingest_flow(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        package_response = client.post(
            "/api/v1/documents/package-gotd",
            files=[
                ("files", ("core_notes.txt", _load_sample("sample_epc.txt"), "text/plain")),
                ("files", ("core_web.html", _load_sample("sample_5gc.html"), "text/html")),
            ],
            data={
                "library_name": "Core Library",
                "product": "Golibas Core",
                "vendor": "Golibas Telecom",
                "domain": "5gc",
                "release": "R17",
            },
        )
        assert package_response.status_code == 200
        assert package_response.content.startswith(b"PK")

        with zipfile.ZipFile(BytesIO(package_response.content), "r") as archive:
            assert "manifest.json" in archive.namelist()
            assert any(name.startswith("files/") for name in archive.namelist())

        upload_response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("core_library.gotd", package_response.content, "application/octet-stream")},
            data={
                "title": "Core Library",
                "product": "Golibas Core",
                "vendor": "Golibas Telecom",
                "domain": "5gc",
                "release": "R17",
            },
        )

        assert upload_response.status_code == 200
        upload_payload = upload_response.json()
        assert upload_payload["source_format"] == "gotd"
        assert upload_payload["library_items"] == 2
        assert len(upload_payload["ingested_document_ids"]) == 2

        tree_response = client.get("/api/v1/documents/tree")
        assert tree_response.status_code == 200
        tree_payload = tree_response.json()
        assert any(product["name"] == "Golibas Core" for product in tree_payload["products"])

    app.dependency_overrides.clear()
    settings.storage_db_path = original_db_path


def test_gotd_invalid_archive_returns_400(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        upload_response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("broken.gotd", b"not-a-zip", "application/octet-stream")},
            data={
                "title": "Broken Library",
                "product": "Golibas Core",
                "vendor": "Golibas Telecom",
            },
        )

        assert upload_response.status_code == 400
        assert upload_response.json()["detail"] == "Invalid .gotd archive"

    app.dependency_overrides.clear()
    settings.storage_db_path = original_db_path


def test_auth_password_and_sms_flow(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        password_response = client.post(
            "/api/v1/auth/login/password",
            json={"login": "admin", "password": "admin123"},
        )
        assert password_response.status_code == 200
        password_payload = password_response.json()
        assert password_payload["success"] is True
        assert password_payload["method"] == "password"
        assert password_payload["access_token"]
        assert password_payload["role"] == "admin"

        sms_send_response = client.post(
            "/api/v1/auth/sms/send-code",
            json={"phone": "+79001112233"},
        )
        assert sms_send_response.status_code == 200
        sms_send_payload = sms_send_response.json()
        assert sms_send_payload["success"] is True
        demo_code = sms_send_payload["demo_code"]
        assert demo_code

        sms_verify_response = client.post(
            "/api/v1/auth/sms/verify",
            json={"phone": "+79001112233", "code": demo_code},
        )
        assert sms_verify_response.status_code == 200
        sms_verify_payload = sms_verify_response.json()
        assert sms_verify_payload["success"] is True
        assert sms_verify_payload["method"] == "sms"

    app.dependency_overrides.clear()
    settings.storage_db_path = original_db_path


def test_auth_qr_flow(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        qr_create_response = client.post("/api/v1/auth/qr/create")
        assert qr_create_response.status_code == 200
        qr_create_payload = qr_create_response.json()
        session_id = qr_create_payload["session_id"]
        assert qr_create_payload["qr_image_data_url"].startswith("data:image/png;base64,")

        qr_status_pending_response = client.get(f"/api/v1/auth/qr/status/{session_id}")
        assert qr_status_pending_response.status_code == 200
        assert qr_status_pending_response.json()["status"] == "pending"

        qr_confirm_response = client.post(
            "/api/v1/auth/qr/confirm",
            json={"session_id": session_id},
        )
        assert qr_confirm_response.status_code == 200
        assert qr_confirm_response.json()["method"] == "qr"

        qr_status_confirmed_response = client.get(f"/api/v1/auth/qr/status/{session_id}")
        assert qr_status_confirmed_response.status_code == 200
        qr_status_confirmed_payload = qr_status_confirmed_response.json()
        assert qr_status_confirmed_payload["status"] == "confirmed"
        assert qr_status_confirmed_payload["access_token"]

    app.dependency_overrides.clear()
    settings.storage_db_path = original_db_path


def test_registration_flow_and_validation_rules(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        invalid_validate_response = client.post(
            "/api/v1/auth/register/validate",
            json={"login": "new_user", "password": "1234567", "phone": "+79001112233"},
        )
        assert invalid_validate_response.status_code == 200
        invalid_validate_payload = invalid_validate_response.json()
        assert invalid_validate_payload["valid"] is False
        assert any("минимум 8" in message for message in invalid_validate_payload["errors"])

        start_response = client.post(
            "/api/v1/auth/register/start",
            json={"login": "new_user", "password": "StrongPass1", "email": "new_user@example.com"},
        )
        assert start_response.status_code == 200
        start_payload = start_response.json()
        challenge_id = start_payload["challenge_id"]
        demo_code = start_payload["demo_code"]
        assert challenge_id
        assert demo_code

        confirm_response = client.post(
            "/api/v1/auth/register/confirm",
            json={"challenge_id": challenge_id, "code": demo_code},
        )
        assert confirm_response.status_code == 200
        assert confirm_response.json()["method"] == "registration"

        login_response = client.post(
            "/api/v1/auth/login/password",
            json={"login": "new_user", "password": "StrongPass1"},
        )
        assert login_response.status_code == 200

        duplicate_validate_response = client.post(
            "/api/v1/auth/register/validate",
            json={"login": "new_user", "password": "StrongPass2", "email": "another@example.com"},
        )
        assert duplicate_validate_response.status_code == 200
        duplicate_validate_payload = duplicate_validate_response.json()
        assert duplicate_validate_payload["login_available"] is False
        assert duplicate_validate_payload["valid"] is False

    app.dependency_overrides.clear()
    settings.storage_db_path = original_db_path


def test_auth_password_lockout_after_failed_attempts(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        for _ in range(4):
            response = client.post(
                "/api/v1/auth/login/password",
                json={"login": "admin", "password": "wrong-password"},
            )
            assert response.status_code == 401

        lock_response = client.post(
            "/api/v1/auth/login/password",
            json={"login": "admin", "password": "wrong-password"},
        )
        assert lock_response.status_code == 423
        assert "заблокирован" in lock_response.json()["detail"]

        still_locked_response = client.post(
            "/api/v1/auth/login/password",
            json={"login": "admin", "password": "admin123"},
        )
        assert still_locked_response.status_code == 423

        users = list_registered_users()
        admin_user = next(user for user in users if user.login == "admin")
        assert admin_user.failed_attempts == 5
        assert admin_user.total_failed_attempts == 5

    app.dependency_overrides.clear()
    settings.storage_db_path = original_db_path


def test_user_admin_management_helpers(tmp_path: Path) -> None:
    original_db_path = _set_test_db(tmp_path)
    try:
        initial_users = list_registered_users()
        assert any(user.login == "admin" for user in initial_users)

        created_user = create_user(
            login="ops_user",
            password="StrongPass1",
            email="ops_user@example.com",
            display_name="Operations",
        )
        assert created_user.login == "ops_user"
        assert created_user.email == "ops_user@example.com"
        assert created_user.total_failed_attempts == 0

        users_after_create = list_registered_users()
        assert any(user.login == "ops_user" for user in users_after_create)

        updated_user = update_user(
            login="ops_user",
            phone="+79001112233",
            email=None,
            display_name="Ops Team",
        )
        assert updated_user.phone == "+79001112233"
        assert updated_user.email is None
        assert updated_user.display_name == "Ops Team"

        delete_user("ops_user")
        users_after_delete = list_registered_users()
        assert all(user.login != "ops_user" for user in users_after_delete)
    finally:
        settings.storage_db_path = original_db_path


def test_metrics_kpi_endpoint_smoke(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        response = client.get("/api/v1/metrics/kpi")
        assert response.status_code == 200

        payload = response.json()
        assert payload["indexed_documents_total"] == 0
        assert isinstance(payload["search_latency_p95_ms"], float)
        assert payload["search_latency_p95_ms"] >= 0.0
        assert isinstance(payload["search_samples"], int)
        assert payload["search_samples"] >= 0

    app.dependency_overrides.clear()
    settings.storage_db_path = original_db_path


def test_ai_context_retrieval_pipeline(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        client.post("/api/v1/documents/index/bootstrap")

        upload_response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("sample_epc.txt", _load_sample("sample_epc.txt"), "text/plain")},
            data={
                "title": "Ericsson EPC Mobility Management Guide",
                "product": "Ericsson Packet Core",
                "vendor": "Ericsson",
                "domain": "epc",
                "release": "R16",
            },
        )
        assert upload_response.status_code == 200
        uploaded_doc_id = upload_response.json()["doc_id"]

        ai_response = client.post(
            "/api/v1/ai/ask",
            json={
                "question": "paging",
                "context_doc_ids": [uploaded_doc_id],
                "max_citations": 3,
            },
        )

        assert ai_response.status_code == 200
        payload = ai_response.json()
        assert payload["citations"]
        assert len(payload["citations"]) <= 3
        assert payload["citations"][0]["doc_id"] == uploaded_doc_id
        assert "контекст" in payload["answer"].lower()
        assert payload["confidence"] > 0.0
        assert payload["source_policy"] == "strict-required-citations"
        assert payload["blocked"] is False
        assert payload["trace_id"]
        assert payload["retrieval_stats"]["returned_citations"] >= 1

        compare_response = client.post(
            "/api/v1/ai/ask",
            json={
                "question": "paging",
                "context_doc_ids": [uploaded_doc_id],
                "max_citations": 3,
                "mode": "compare",
            },
        )
        assert compare_response.status_code == 200
        assert "сравнение" in compare_response.json()["answer"].lower()

        diagnose_response = client.post(
            "/api/v1/ai/ask",
            json={
                "question": "paging",
                "context_doc_ids": [uploaded_doc_id],
                "max_citations": 3,
                "mode": "diagnose",
            },
        )
        assert diagnose_response.status_code == 200
        assert "диагностика" in diagnose_response.json()["answer"].lower()

        blocked_response = client.post(
            "/api/v1/ai/ask",
            json={
                "question": "nonexistent-query-token",
                "context_doc_ids": [uploaded_doc_id],
                "max_citations": 3,
                "mode": "explain",
            },
        )
        assert blocked_response.status_code == 200
        blocked_payload = blocked_response.json()
        assert blocked_payload["blocked"] is True
        assert blocked_payload["citations"] == []
        assert blocked_payload["confidence"] == 0.0
        assert "заблокирован" in blocked_payload["answer"].lower()

    app.dependency_overrides.clear()
    settings.storage_db_path = original_db_path


def test_ai_feedback_cycle_by_trace_id(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        client.post("/api/v1/documents/index/bootstrap")

        upload_response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("sample_epc.txt", _load_sample("sample_epc.txt"), "text/plain")},
            data={
                "title": "Ericsson EPC Mobility Management Guide",
                "product": "Ericsson Packet Core",
                "vendor": "Ericsson",
                "domain": "epc",
                "release": "R16",
            },
        )
        assert upload_response.status_code == 200
        uploaded_doc_id = upload_response.json()["doc_id"]

        ai_response = client.post(
            "/api/v1/ai/ask",
            json={
                "question": "paging",
                "context_doc_ids": [uploaded_doc_id],
                "max_citations": 3,
                "mode": "explain",
            },
        )
        assert ai_response.status_code == 200
        trace_id = ai_response.json()["trace_id"]

        feedback_response = client.post(
            "/api/v1/ai/feedback",
            json={
                "trace_id": trace_id,
                "vote": "like",
                "reason": "Ответ соответствует ожидаемому контексту.",
            },
        )
        assert feedback_response.status_code == 200
        feedback_payload = feedback_response.json()
        assert feedback_payload["saved"] is True
        assert feedback_payload["trace_id"] == trace_id
        assert feedback_payload["vote"] == "like"
        assert feedback_payload["feedback_id"]

        stored = get_ai_feedback_by_trace(trace_id)
        assert len(stored) == 1
        assert stored[0]["vote"] == "like"
        assert stored[0]["reason"] == "Ответ соответствует ожидаемому контексту."

    app.dependency_overrides.clear()
    settings.storage_db_path = original_db_path


def test_admin_rbac_and_audit_log_flow(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        unauthorized_response = client.get("/api/v1/admin/users")
        assert unauthorized_response.status_code == 401

        admin_login_response = client.post(
            "/api/v1/auth/login/password",
            json={"login": "admin", "password": "admin123"},
        )
        assert admin_login_response.status_code == 200
        admin_token = admin_login_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        create_user_response = client.post(
            "/api/v1/admin/users",
            json={
                "login": "phase4_user",
                "password": "StrongPass1",
                "display_name": "Phase 4 User",
                "role": "user",
                "email": "phase4_user@example.com",
            },
            headers=admin_headers,
        )
        assert create_user_response.status_code == 200
        assert create_user_response.json()["role"] == "user"

        user_login_response = client.post(
            "/api/v1/auth/login/password",
            json={"login": "phase4_user", "password": "StrongPass1"},
        )
        assert user_login_response.status_code == 200
        user_token = user_login_response.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        forbidden_response = client.get("/api/v1/admin/users", headers=user_headers)
        assert forbidden_response.status_code == 403

        delete_user_response = client.delete("/api/v1/admin/users/phase4_user", headers=admin_headers)
        assert delete_user_response.status_code == 200
        assert delete_user_response.json()["deleted"] is True

        audit_response = client.get("/api/v1/admin/audit?limit=20", headers=admin_headers)
        assert audit_response.status_code == 200
        actions = [item["action"] for item in audit_response.json()]
        assert "admin.user.create" in actions
        assert "admin.user.delete" in actions

        storage_audit = get_admin_audit_events(limit=20)
        assert any(item["action"] == "admin.user.create" and item["status"] == "success" for item in storage_audit)
        assert any(item["action"] == "admin.user.delete" and item["status"] == "success" for item in storage_audit)

    app.dependency_overrides.clear()
    settings.storage_db_path = original_db_path
