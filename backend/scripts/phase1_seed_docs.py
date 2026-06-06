from __future__ import annotations

import argparse
from pathlib import Path
import sys

from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app  # noqa: E402
from app.services.opensearch_client import get_opensearch_client  # noqa: E402


class _FakeIndices:
    def __init__(self, client: "_FakeOpenSearch"):
        self._client = client

    def exists(self, index: str) -> bool:
        return index in self._client.indexes

    def create(self, index: str, body: dict) -> dict:
        self._client.indexes[index] = body
        return {"acknowledged": True}


class _FakeOpenSearch:
    def __init__(self) -> None:
        self.indexes: dict[str, dict] = {}
        self.documents: dict[str, dict] = {}
        self.indices = _FakeIndices(self)

    def bulk(self, body: list[dict], refresh: bool = False) -> dict:
        for offset in range(0, len(body), 2):
            action = body[offset]["index"]
            document = body[offset + 1]
            self.documents[action["_id"]] = document
        return {"errors": False}


def _build_payload(index: int) -> tuple[dict, dict]:
    file_name = f"phase1_doc_{index:04d}.txt"
    content = (
        f"Core EPC/5GC troubleshooting note #{index}. "
        "AMF handles access and mobility. "
        "SMF manages sessions and interacts with UPF."
    ).encode("utf-8")

    files = {"file": (file_name, content, "text/plain")}
    data = {
        "title": f"Phase1 Synthetic Document {index:04d}",
        "product": "Phase1 Synthetic Library",
        "vendor": "Golibas",
        "domain": "5gc",
        "release": "R17",
        "node_type": "AMF",
        "interface": "N2",
        "protocol": "HTTP/2",
        "language": "en",
        "source_path": f"synthetic/{file_name}",
    }
    return files, data


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed synthetic documents for Phase 1 KPI criteria")
    parser.add_argument("--count", type=int, default=300, help="How many synthetic documents to ingest")
    args = parser.parse_args()

    if args.count <= 0:
        print("[FAIL] count must be > 0")
        return 2

    fake_client = _FakeOpenSearch()
    app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    success = 0
    with TestClient(app) as client:
        for index in range(1, args.count + 1):
            files, data = _build_payload(index)
            response = client.post("/api/v1/documents/upload", files=files, data=data)
            if response.status_code != 200:
                print(f"[FAIL] upload #{index}: status={response.status_code}, body={response.text}")
                app.dependency_overrides.clear()
                return 1
            success += 1

    app.dependency_overrides.clear()
    print(f"[PASS] Seeded documents: {success}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
