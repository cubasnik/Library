from opensearchpy import OpenSearch
import re
import time

from app.config import settings
from app.schemas import SearchFilters, SearchHit, SearchRequest, SearchResponse
from app.services.metrics_service import record_stage_timing


FILTER_FIELD_MAP = {
    "product": "product",
    "vendor": "vendor",
    "domain": "domain",
    "release": "release",
    "node_type": "node_type",
    "interface": "interface",
    "protocol": "protocol",
}


def _build_filters(filters: SearchFilters) -> list[dict]:
    clauses: list[dict] = []
    filter_data = filters.model_dump()

    for request_field, index_field in FILTER_FIELD_MAP.items():
        values = filter_data.get(request_field, [])
        if values:
            clauses.append({"terms": {f"{index_field}.keyword": values}})

    return clauses


def _build_search_query(payload: SearchRequest) -> dict:
    offset = (payload.page - 1) * payload.size
    filter_clauses = _build_filters(payload.filters)

    return {
        "from": offset,
        "size": payload.size,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": payload.query,
                            "fields": ["title^3", "content", "vendor^1.5", "domain^1.5", "interface^1.2"],
                            "type": "best_fields",
                            "operator": "and",
                        }
                    }
                ],
                "should": [
                    {
                        "multi_match": {
                            "query": payload.query,
                            "fields": ["title^4", "content^1.2"],
                            "type": "phrase",
                            "boost": 2.0,
                        }
                    },
                    {
                        "multi_match": {
                            "query": payload.query,
                            "fields": ["title^2", "content"],
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                            "boost": 0.4,
                        }
                    },
                ],
                "minimum_should_match": 0,
                "filter": filter_clauses,
            }
        },
        "highlight": {
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"],
            "fields": {"content": {"fragment_size": 200, "number_of_fragments": 1}},
        },
        "aggs": {
            "products": {"terms": {"field": "product.keyword", "size": 20}},
            "vendors": {"terms": {"field": "vendor.keyword", "size": 20}},
            "domains": {"terms": {"field": "domain.keyword", "size": 20}},
            "releases": {"terms": {"field": "release.keyword", "size": 20}},
            "node_types": {"terms": {"field": "node_type.keyword", "size": 20}},
            "interfaces": {"terms": {"field": "interface.keyword", "size": 20}},
            "protocols": {"terms": {"field": "protocol.keyword", "size": 20}},
        },
    }


def _tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"\W+", text.lower()) if token]


def _rerank_hits(payload: SearchRequest, hits_data: list[dict]) -> list[dict]:
    if not hits_data:
        return []

    scores = [float(item.get("_score", 0.0)) for item in hits_data]
    max_score = max(scores) if scores else 1.0
    if max_score <= 0:
        max_score = 1.0

    query_tokens = set(_tokenize(payload.query))
    reranked: list[dict] = []

    for item in hits_data:
        src = item.get("_source", {})
        raw_score = float(item.get("_score", 0.0))
        normalized_score = raw_score / max_score

        text_blob = " ".join(
            [
                str(src.get("title", "")),
                str(src.get("content", "")),
                str(src.get("vendor", "")),
                str(src.get("domain", "")),
                str(src.get("release", "")),
                str(src.get("node_type", "")),
                str(src.get("interface", "")),
                str(src.get("protocol", "")),
            ]
        ).lower()
        doc_tokens = set(_tokenize(text_blob))

        coverage = 0.0
        if query_tokens:
            coverage = len(query_tokens.intersection(doc_tokens)) / len(query_tokens)

        metadata_bonus = 0.0
        for field_name in ("vendor", "domain", "release", "node_type", "interface", "protocol"):
            value = str(src.get(field_name, "")).lower()
            if value and value in text_blob and value in payload.query.lower():
                metadata_bonus += 0.02
        metadata_bonus = min(metadata_bonus, 0.1)

        hybrid_score = round(normalized_score * 0.65 + coverage * 0.25 + metadata_bonus * 0.1, 6)
        reranked.append({"item": item, "hybrid_score": hybrid_score})

    reranked.sort(key=lambda value: value["hybrid_score"], reverse=True)
    return reranked


def search_docs(client: OpenSearch, payload: SearchRequest) -> SearchResponse:
    query = _build_search_query(payload)

    # Graceful fallback for empty/non-initialized index to keep MVP endpoint stable.
    opensearch_started_at = time.perf_counter()
    try:
        raw = client.search(index=settings.opensearch_index, body=query)
    except Exception:
        return SearchResponse(total=0, page=payload.page, size=payload.size, hits=[], facets={})
    record_stage_timing("search.opensearch", (time.perf_counter() - opensearch_started_at) * 1000.0)

    total = raw.get("hits", {}).get("total", {}).get("value", 0)
    hits_data = raw.get("hits", {}).get("hits", [])
    rerank_started_at = time.perf_counter()
    reranked_hits = _rerank_hits(payload, hits_data)
    record_stage_timing("search.rerank", (time.perf_counter() - rerank_started_at) * 1000.0)

    hits: list[SearchHit] = []
    for reranked in reranked_hits:
        item = reranked["item"]
        src = item.get("_source", {})
        highlight = item.get("highlight", {}).get("content", [])
        snippet = highlight[0] if highlight else src.get("content", "")[:240]

        hits.append(
            SearchHit(
                doc_id=str(src.get("doc_id", "")),
                chunk_id=str(src.get("chunk_id", "")),
                title=str(src.get("title", "Untitled")),
                snippet=snippet,
                score=float(reranked["hybrid_score"]),
                vendor=src.get("vendor"),
                domain=src.get("domain"),
                release=src.get("release"),
                node_type=src.get("node_type"),
                interface=src.get("interface"),
                protocol=src.get("protocol"),
            )
        )

    aggs = raw.get("aggregations", {})
    def _normalize_buckets(values: list[dict]) -> list[dict]:
        return [{"key": item.get("key"), "count": item.get("doc_count", 0)} for item in values if item.get("key")]

    facets = {
        "product": _normalize_buckets(aggs.get("products", {}).get("buckets", [])),
        "vendor": _normalize_buckets(aggs.get("vendors", {}).get("buckets", [])),
        "domain": _normalize_buckets(aggs.get("domains", {}).get("buckets", [])),
        "release": _normalize_buckets(aggs.get("releases", {}).get("buckets", [])),
        "node_type": _normalize_buckets(aggs.get("node_types", {}).get("buckets", [])),
        "interface": _normalize_buckets(aggs.get("interfaces", {}).get("buckets", [])),
        "protocol": _normalize_buckets(aggs.get("protocols", {}).get("buckets", [])),
    }

    return SearchResponse(total=total, page=payload.page, size=payload.size, hits=hits, facets=facets)
