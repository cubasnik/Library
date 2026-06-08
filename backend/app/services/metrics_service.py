from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
import math
import threading

from app.services.storage_service import count_documents


_LOCK = threading.Lock()
_SEARCH_LATENCY_MS = deque(maxlen=1000)
_AI_LATENCY_MS = deque(maxlen=1000)
_UPLOAD_EVENTS = deque(maxlen=5000)
_ERROR_COUNTS: dict[str, int] = {}
_HOTSPOT_STAGE_SAMPLES: dict[str, deque[float]] = {}
_HOTSPOT_STAGE_MAX_SAMPLES = 1000


def record_search_latency_ms(latency_ms: float) -> None:
    with _LOCK:
        _SEARCH_LATENCY_MS.append(max(0.0, float(latency_ms)))


def get_search_latency_p95_ms() -> float:
    with _LOCK:
        values = list(_SEARCH_LATENCY_MS)
    if not values:
        return 0.0
    values.sort()
    rank = max(1, math.ceil(0.95 * len(values)))
    return round(values[rank - 1], 2)


def get_search_samples_count() -> int:
    with _LOCK:
        return len(_SEARCH_LATENCY_MS)


def record_ai_latency_ms(latency_ms: float) -> None:
    with _LOCK:
        _AI_LATENCY_MS.append(max(0.0, float(latency_ms)))


def get_ai_latency_p95_ms() -> float:
    with _LOCK:
        values = list(_AI_LATENCY_MS)
    if not values:
        return 0.0
    values.sort()
    rank = max(1, math.ceil(0.95 * len(values)))
    return round(values[rank - 1], 2)


def get_ai_samples_count() -> int:
    with _LOCK:
        return len(_AI_LATENCY_MS)


def record_upload_event(*, success: bool, docs: int, chunks: int) -> None:
    now = datetime.now(timezone.utc)
    with _LOCK:
        _UPLOAD_EVENTS.append(
            {
                "timestamp": now,
                "success": bool(success),
                "docs": max(0, int(docs)),
                "chunks": max(0, int(chunks)),
            }
        )


def _filter_recent_upload_events(window_seconds: int = 300) -> list[dict]:
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(seconds=window_seconds)
    with _LOCK:
        return [event for event in _UPLOAD_EVENTS if event["timestamp"] >= threshold]


def get_upload_counters() -> tuple[int, int]:
    with _LOCK:
        success = sum(1 for event in _UPLOAD_EVENTS if event["success"])
        failures = sum(1 for event in _UPLOAD_EVENTS if not event["success"])
    return success, failures


def get_upload_throughput_per_min(window_seconds: int = 300) -> tuple[float, float]:
    events = _filter_recent_upload_events(window_seconds=window_seconds)
    if not events:
        return 0.0, 0.0

    minutes = max(window_seconds / 60.0, 1.0)
    docs_total = sum(event["docs"] for event in events if event["success"])
    chunks_total = sum(event["chunks"] for event in events if event["success"])
    return round(docs_total / minutes, 2), round(chunks_total / minutes, 2)


def record_error(error_type: str) -> None:
    normalized = (error_type or "unknown").strip().lower()
    if not normalized:
        normalized = "unknown"
    with _LOCK:
        _ERROR_COUNTS[normalized] = _ERROR_COUNTS.get(normalized, 0) + 1


def get_error_counts() -> dict[str, int]:
    with _LOCK:
        return dict(_ERROR_COUNTS)


def record_stage_timing(stage: str, latency_ms: float) -> None:
    normalized_stage = (stage or "unknown").strip().lower()
    if not normalized_stage:
        normalized_stage = "unknown"
    value = max(0.0, float(latency_ms))
    with _LOCK:
        samples = _HOTSPOT_STAGE_SAMPLES.get(normalized_stage)
        if samples is None:
            samples = deque(maxlen=_HOTSPOT_STAGE_MAX_SAMPLES)
            _HOTSPOT_STAGE_SAMPLES[normalized_stage] = samples
        samples.append(value)


def get_hotspot_stats() -> list[dict]:
    def _p95(values: list[float]) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        rank = max(1, math.ceil(0.95 * len(ordered)))
        return round(ordered[rank - 1], 2)

    stats: list[dict] = []
    with _LOCK:
        snapshot = {stage: list(values) for stage, values in _HOTSPOT_STAGE_SAMPLES.items()}

    for stage, values in snapshot.items():
        if not values:
            continue
        avg = round(sum(values) / len(values), 2)
        stats.append(
            {
                "stage": stage,
                "count": len(values),
                "avg_ms": avg,
                "p95_ms": _p95(values),
            }
        )

    stats.sort(key=lambda item: (item["p95_ms"], item["avg_ms"]), reverse=True)
    return stats


def get_indexed_documents_total() -> int:
    return count_documents()