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

    def search(self, index: str, body: dict) -> dict:
        query_text = body["query"]["bool"]["must"][0]["multi_match"]["query"].lower()
        hits = []
        for document_id, document in self.documents.items():
            haystack = f"{document.get('title', '')} {document.get('content', '')}".lower()
            if query_text in haystack:
                hits.append(
                    {
                        "_id": document_id,
                        "_score": 1.0,
                        "_source": document,
                        "highlight": {"content": [document.get("content", "")[:240]]},
                    }
                )
        return {
            "hits": {"total": {"value": len(hits)}, "hits": hits},
            "aggregations": {
                "products": {"buckets": []},
                "vendors": {"buckets": []},
                "domains": {"buckets": []},
                "releases": {"buckets": []},
                "node_types": {"buckets": []},
                "interfaces": {"buckets": []},
                "protocols": {"buckets": []},
            },
        }


def _check(name: str, passed: bool, details: str) -> bool:
    print(f"[{ 'PASS' if passed else 'FAIL' }] {name}: {details}")
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 gate checks")
    parser.add_argument("--min-docs", type=int, default=300, help="Minimum indexed documents required")
    parser.add_argument("--search-runs", type=int, default=30, help="How many repeated search requests to run")
    parser.add_argument("--p95-ms", type=float, default=300.0, help="Target p95 latency threshold in ms")
    parser.add_argument(
        "--offline-search",
        action="store_true",
        help="Use built-in fake OpenSearch for gate checks (recommended if OpenSearch is not running)",
    )
    args = parser.parse_args()

    all_passed = True

    if args.offline_search:
        fake_client = _FakeOpenSearch()
        app.dependency_overrides[get_opensearch_client] = lambda: fake_client

    with TestClient(app) as client:
        kpi_response = client.get("/api/v1/metrics/kpi")
        if kpi_response.status_code != 200:
            _check("kpi endpoint", False, f"status={kpi_response.status_code}")
            print("PHASE1_GATE=FAIL")
            return 1

        kpi_payload = kpi_response.json()
        doc_count = int(kpi_payload.get("indexed_documents_total", 0))
        all_passed = _check(
            "indexed documents",
            doc_count >= args.min_docs,
            f"actual={doc_count}, required>={args.min_docs}",
        ) and all_passed

        search_success = True
        for _ in range(args.search_runs):
            response = client.post(
                "/api/v1/search",
                json={"query": "AMF", "page": 1, "size": 10, "filters": {}},
            )
            if response.status_code != 200:
                search_success = False
                break
            payload = response.json()
            if not isinstance(payload.get("facets"), dict):
                search_success = False
                break

        all_passed = _check(
            "faceted search stability",
            search_success,
            f"runs={args.search_runs}",
        ) and all_passed

        kpi_after_search = client.get("/api/v1/metrics/kpi")
        if kpi_after_search.status_code != 200:
            all_passed = _check("search p95", False, f"kpi status={kpi_after_search.status_code}") and all_passed
        else:
            p95_ms = float(kpi_after_search.json().get("search_latency_p95_ms", 0.0))
            samples = int(kpi_after_search.json().get("search_samples", 0))
            all_passed = _check(
                "search p95",
                p95_ms <= args.p95_ms,
                f"p95={p95_ms:.2f}ms, threshold={args.p95_ms:.2f}ms, samples={samples}",
            ) and all_passed

    app.dependency_overrides.clear()

    print("PHASE1_GATE=PASS" if all_passed else "PHASE1_GATE=FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
