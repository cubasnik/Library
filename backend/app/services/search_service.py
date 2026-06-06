from opensearchpy import OpenSearch

from app.config import settings
from app.schemas import SearchFilters, SearchHit, SearchRequest, SearchResponse


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
                            "fields": ["title^2", "content"],
                            "type": "best_fields",
                            "operator": "and",
                        }
                    }
                ],
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


def search_docs(client: OpenSearch, payload: SearchRequest) -> SearchResponse:
    query = _build_search_query(payload)

    # Graceful fallback for empty/non-initialized index to keep MVP endpoint stable.
    try:
        raw = client.search(index=settings.opensearch_index, body=query)
    except Exception:
        return SearchResponse(total=0, page=payload.page, size=payload.size, hits=[], facets={})

    total = raw.get("hits", {}).get("total", {}).get("value", 0)
    hits_data = raw.get("hits", {}).get("hits", [])

    hits: list[SearchHit] = []
    for item in hits_data:
        src = item.get("_source", {})
        highlight = item.get("highlight", {}).get("content", [])
        snippet = highlight[0] if highlight else src.get("content", "")[:240]

        hits.append(
            SearchHit(
                doc_id=str(src.get("doc_id", "")),
                chunk_id=str(src.get("chunk_id", "")),
                title=str(src.get("title", "Untitled")),
                snippet=snippet,
                score=float(item.get("_score", 0.0)),
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
