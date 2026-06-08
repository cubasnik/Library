from __future__ import annotations

import argparse
from pathlib import Path
import sys

from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app  # noqa: E402


def _print_stage(title: str, passed: bool, details: str) -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {title}: {details}")
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5 performance gate checks")
    parser.add_argument("--search-p95-ms", type=float, default=400.0)
    parser.add_argument("--ai-p95-ms", type=float, default=600.0)
    parser.add_argument("--parse-p95-ms", type=float, default=800.0)
    parser.add_argument("--rerank-p95-ms", type=float, default=120.0)
    args = parser.parse_args()

    all_passed = True
    with TestClient(app) as client:
        panels = client.get("/api/v1/metrics/panels")
        if panels.status_code != 200:
            print("PHASE5_GATE=FAIL")
            print("metrics/panels unavailable")
            return 1

        panels_payload = panels.json()
        search_p95 = float(panels_payload.get("search_latency_p95_ms", 0.0))
        ai_p95 = float(panels_payload.get("ai_latency_p95_ms", 0.0))

        all_passed = _print_stage(
            "search latency p95",
            search_p95 <= args.search_p95_ms,
            f"actual={search_p95:.2f}ms threshold<={args.search_p95_ms:.2f}ms",
        ) and all_passed

        all_passed = _print_stage(
            "ai latency p95",
            ai_p95 <= args.ai_p95_ms,
            f"actual={ai_p95:.2f}ms threshold<={args.ai_p95_ms:.2f}ms",
        ) and all_passed

        hotspots = client.get("/api/v1/metrics/hotspots")
        if hotspots.status_code != 200:
            print("PHASE5_GATE=FAIL")
            print("metrics/hotspots unavailable")
            return 1

        hotspot_items = hotspots.json().get("hotspots", [])
        by_stage = {item["stage"]: item for item in hotspot_items}

        parse_p95 = float(by_stage.get("upload.parse.pdf", by_stage.get("upload.parse.text", {"p95_ms": 0.0})) ["p95_ms"])
        rerank_p95 = float(by_stage.get("search.rerank", {"p95_ms": 0.0})["p95_ms"])

        all_passed = _print_stage(
            "upload parse hotspot",
            parse_p95 <= args.parse_p95_ms,
            f"actual={parse_p95:.2f}ms threshold<={args.parse_p95_ms:.2f}ms",
        ) and all_passed

        all_passed = _print_stage(
            "rerank hotspot",
            rerank_p95 <= args.rerank_p95_ms,
            f"actual={rerank_p95:.2f}ms threshold<={args.rerank_p95_ms:.2f}ms",
        ) and all_passed

        go_needed = parse_p95 > args.parse_p95_ms
        cpp_needed = rerank_p95 > args.rerank_p95_ms

        print("RECOMMENDATION_GO_WORKERS=YES" if go_needed else "RECOMMENDATION_GO_WORKERS=NO")
        print("RECOMMENDATION_CPP_PARSERS=YES" if cpp_needed else "RECOMMENDATION_CPP_PARSERS=NO")

    print("PHASE5_GATE=PASS" if all_passed else "PHASE5_GATE=FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
