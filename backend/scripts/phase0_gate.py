from __future__ import annotations

from fastapi.testclient import TestClient
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app


CHECKS = [
    ("health", "GET", "/health", None, 200),
    ("openapi", "GET", "/openapi.json", None, 200),
    (
        "search",
        "POST",
        "/api/v1/search",
        {"query": "paging", "page": 1, "size": 10, "filters": {}},
        200,
    ),
    (
        "ai",
        "POST",
        "/api/v1/ai/ask",
        {"question": "Что такое AMF?", "context_doc_ids": [], "max_citations": 3},
        200,
    ),
]


def main() -> int:
    all_passed = True
    with TestClient(app) as client:
        for name, method, url, payload, expected_status in CHECKS:
            if method == "GET":
                response = client.get(url)
            else:
                response = client.post(url, json=payload)

            passed = response.status_code == expected_status
            all_passed = all_passed and passed
            print(
                f"[{ 'PASS' if passed else 'FAIL' }] {name}: "
                f"status={response.status_code}, expected={expected_status}"
            )

    print("PHASE0_GATE=PASS" if all_passed else "PHASE0_GATE=FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
