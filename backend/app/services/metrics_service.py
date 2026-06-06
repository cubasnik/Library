from __future__ import annotations

from collections import deque
import math
import threading

from app.services.storage_service import count_documents


_LOCK = threading.Lock()
_SEARCH_LATENCY_MS = deque(maxlen=1000)


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


def get_indexed_documents_total() -> int:
    return count_documents()