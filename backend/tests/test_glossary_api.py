from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import create_user
from app.services.opensearch_client import get_opensearch_client
from app.services.storage_service import glossary_entries_count
from tests.test_phase1_smoke import FakeOpenSearch, _set_test_db


def test_glossary_public_read_seeds_from_json(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        response = client.get("/api/v1/glossary")
        assert response.status_code == 200
        payload = response.json()
        assert payload
        assert payload[0]["abbr"] == "AMF"
        assert glossary_entries_count() > 0

    app.dependency_overrides.clear()
    from app.config import settings
    settings.storage_db_path = original_db_path


def test_glossary_admin_crud_and_import_export(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        login_response = client.post(
            "/api/v1/auth/login/password",
            json={"login": "admin", "password": "admin123"},
        )
        assert login_response.status_code == 200
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        create_response = client.post(
            "/api/v1/glossary",
            json={
                "abbr": "ZZAPI",
                "term_ru": "Тест API",
                "term_en": "API test",
                "definition_ru": "Описание",
                "definition_en": "Description",
                "related": ["AMF"],
                "keywords": ["api"],
                "manual_sources": [],
            },
            headers=headers,
        )
        assert create_response.status_code == 200
        assert create_response.json()["abbr"] == "ZZAPI"

        update_response = client.patch(
            "/api/v1/glossary/ZZAPI",
            json={
                "abbr": "ZZAPI",
                "term_ru": "Тест API 2",
                "term_en": "API test 2",
                "definition_ru": "Описание 2",
                "definition_en": "Description 2",
                "related": ["SMF"],
                "keywords": ["api2"],
                "manual_sources": [],
            },
            headers=headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["term_ru"] == "Тест API 2"

        export_response = client.get("/api/v1/glossary/export", headers=headers)
        assert export_response.status_code == 200
        export_payload = export_response.json()
        assert any(item["abbr"] == "ZZAPI" for item in export_payload["entries"])

        import_response = client.post(
            "/api/v1/glossary/import",
            json={
                "replace_existing": False,
                "entries": [
                    {
                        "abbr": "ZZIMP",
                        "term_ru": "Импортированный термин",
                        "term_en": "Imported term",
                        "definition_ru": "Импорт RU",
                        "definition_en": "Import EN",
                        "related": [],
                        "keywords": ["import"],
                        "manual_sources": [],
                    }
                ],
            },
            headers=headers,
        )
        assert import_response.status_code == 200
        assert import_response.json()["replace_existing"] is False

        delete_response = client.delete("/api/v1/glossary/ZZAPI", headers=headers)
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted"] is True

    app.dependency_overrides.clear()
    from app.config import settings
    settings.storage_db_path = original_db_path


def test_glossary_admin_access_control(tmp_path: Path) -> None:
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        unauthorized = client.post(
            "/api/v1/glossary",
            json={
                "abbr": "ZZNOAUTH",
                "term_ru": "Нет доступа",
                "term_en": "No access",
                "definition_ru": "Описание",
                "definition_en": "Description",
                "related": [],
                "keywords": [],
                "manual_sources": [],
            },
        )
        assert unauthorized.status_code == 401

        admin_login = client.post(
            "/api/v1/auth/login/password",
            json={"login": "admin", "password": "admin123"},
        )
        assert admin_login.status_code == 200
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        create_user(
            login="glossary_user",
            password="StrongPass1",
            role="user",
            display_name="Glossary User",
        )
        user_login = client.post(
            "/api/v1/auth/login/password",
            json={"login": "glossary_user", "password": "StrongPass1"},
        )
        assert user_login.status_code == 200
        user_headers = {"Authorization": f"Bearer {user_login.json()['access_token']}"}

        forbidden = client.delete("/api/v1/glossary/AMF", headers=user_headers)
        assert forbidden.status_code == 403

        export_ok = client.get("/api/v1/glossary/export", headers=admin_headers)
        assert export_ok.status_code == 200

    app.dependency_overrides.clear()
    from app.config import settings
    settings.storage_db_path = original_db_path


def test_glossary_admin_e2e_crud_with_audit_and_export(tmp_path: Path) -> None:
    """End-to-end test: admin creates, updates, deletes glossary entry; verifies audit log and export."""
    fake_client = FakeOpenSearch()
    original_db_path = _set_test_db(tmp_path)
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        # Step 1: Admin login
        login_response = client.post(
            "/api/v1/auth/login/password",
            json={"login": "admin", "password": "admin123"},
        )
        assert login_response.status_code == 200
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Step 2: Create new glossary entry
        create_payload = {
            "abbr": "ZZSMOKE01",
            "term_ru": "Тестовый термин для smoke",
            "term_en": "Smoke test term",
            "definition_ru": "Создано для проверки CRUD в UI.",
            "definition_en": "Created to validate UI CRUD flow.",
            "related": ["AMF", "SMF"],
            "keywords": ["smoke", "test", "glossary"],
            "manual_sources": [],
        }
        create_response = client.post(
            "/api/v1/glossary",
            json=create_payload,
            headers=headers,
        )
        assert create_response.status_code == 200
        entry_id = create_response.json()["abbr"]
        assert entry_id == "ZZSMOKE01"

        # Step 3: Verify entry exists in public glossary
        public_response = client.get("/api/v1/glossary")
        assert public_response.status_code == 200
        entries = public_response.json()
        abbrs = [e["abbr"] for e in entries]
        assert "ZZSMOKE01" in abbrs

        # Step 4: Update entry
        update_payload = {
            "abbr": "ZZSMOKE01",
            "term_ru": "Тестовый термин для smoke (обновлен)",
            "term_en": "Smoke test term",
            "definition_ru": "Обновленное описание на русском.",
            "definition_en": "Updated description in English.",
            "related": ["AMF", "SMF"],
            "keywords": ["smoke", "test", "glossary"],
            "manual_sources": [],
        }
        update_response = client.patch(
            f"/api/v1/glossary/{entry_id}",
            json=update_payload,
            headers=headers,
        )
        assert update_response.status_code == 200
        updated_entry = update_response.json()
        assert updated_entry["term_ru"] == "Тестовый термин для smoke (обновлен)"

        # Step 5: Check audit log includes create and update events
        audit_response = client.get("/api/v1/admin/audit", headers=headers)
        assert audit_response.status_code == 200
        audit_logs = audit_response.json()
        
        # Find create and update events for ZZSMOKE01
        zzsmoke_events = [log for log in audit_logs if log.get("target") == "ZZSMOKE01"]
        assert len(zzsmoke_events) >= 2, f"Expected at least 2 events for ZZSMOKE01, got {len(zzsmoke_events)}"
        
        event_types = [log.get("action") for log in zzsmoke_events]
        assert "admin.glossary.create" in event_types, f"Missing create event in {event_types}"
        assert "admin.glossary.update" in event_types, f"Missing update event in {event_types}"

        # Step 6: Export (template download simulation)
        export_response = client.get("/api/v1/glossary/export", headers=headers)
        assert export_response.status_code == 200
        exported_response = export_response.json()
        assert isinstance(exported_response, dict)
        assert "entries" in exported_response
        exported_data = exported_response["entries"]
        assert isinstance(exported_data, list)
        exported_abbrs = [e.get("abbr") for e in exported_data]
        assert "ZZSMOKE01" in exported_abbrs

        # Step 7: Delete entry
        delete_response = client.delete(
            f"/api/v1/glossary/{entry_id}",
            headers=headers,
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted"] is True

        # Step 8: Verify entry is deleted from public glossary
        public_after_delete = client.get("/api/v1/glossary")
        assert public_after_delete.status_code == 200
        entries_after = public_after_delete.json()
        abbrs_after = [e["abbr"] for e in entries_after]
        assert "ZZSMOKE01" not in abbrs_after

        # Step 9: Verify audit log includes delete event
        audit_final = client.get("/api/v1/admin/audit", headers=headers)
        assert audit_final.status_code == 200
        audit_logs_final = audit_final.json()
        
        zzsmoke_final = [log for log in audit_logs_final if log.get("target") == "ZZSMOKE01"]
        assert len(zzsmoke_final) >= 3, f"Expected at least 3 events after delete, got {len(zzsmoke_final)}"
        
        final_event_types = [log.get("action") for log in zzsmoke_final]
        assert "admin.glossary.delete" in final_event_types, f"Missing delete event in {final_event_types}"

    app.dependency_overrides.clear()
    from app.config import settings
    settings.storage_db_path = original_db_path
