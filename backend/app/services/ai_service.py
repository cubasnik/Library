from __future__ import annotations

from uuid import uuid4

from opensearchpy import OpenSearch

from app.config import settings
from app.schemas import AiAskRequest, AiAskResponse, AiCitation


STRICT_SOURCE_POLICY = "strict-required-citations"


def _build_context_query(payload: AiAskRequest) -> dict:
    filter_clauses: list[dict] = []
    if payload.context_doc_ids:
        filter_clauses.append({"terms": {"doc_id.keyword": payload.context_doc_ids}})

    return {
        "size": payload.max_citations,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": payload.question,
                            "fields": ["title^2", "content"],
                            "type": "best_fields",
                            "operator": "or",
                        }
                    }
                ],
                "filter": filter_clauses,
            }
        },
        "highlight": {
            "pre_tags": ["<mark>"],
            "post_tags": ["</mark>"],
            "fields": {"content": {"fragment_size": 220, "number_of_fragments": 1}},
        },
    }


def _build_citations(raw_hits: list[dict]) -> list[AiCitation]:
    citations: list[AiCitation] = []
    for item in raw_hits:
        src = item.get("_source", {})
        highlight = item.get("highlight", {}).get("content", [])
        snippet = highlight[0] if highlight else str(src.get("content", ""))[:240]

        citations.append(
            AiCitation(
                doc_id=str(src.get("doc_id", "")),
                chunk_id=str(src.get("chunk_id", "")),
                title=str(src.get("title", "Untitled")),
                snippet=snippet,
            )
        )
    return citations


def _build_answer(payload: AiAskRequest, citations: list[AiCitation]) -> str:
    if not citations:
        return (
            "Контекст по индексированным чанкам не найден. "
            "Уточните вопрос или расширьте набор context_doc_ids."
        )

    titles = []
    seen = set()
    for citation in citations:
        if citation.title and citation.title not in seen:
            titles.append(citation.title)
            seen.add(citation.title)

    references = "; ".join(titles[:3])

    if payload.mode == "compare":
        return (
            f"Сравнение по запросу '{payload.question}' выполнено на {len(citations)} найденных чанках. "
            f"Сопоставление опирается на источники: {references}. "
            "Выделите различия в релизах, интерфейсах и ролях сетевых узлов перед применением."
        )

    if payload.mode == "diagnose":
        return (
            f"Диагностика по запросу '{payload.question}' опирается на {len(citations)} релевантных чанков. "
            f"Критичные источники: {references}. "
            "Проверьте последовательность сигнализации и соответствие конфигураций в указанных разделах."
        )

    return (
        f"Объяснение по запросу '{payload.question}' сформировано на {len(citations)} чанках. "
        f"Ключевые источники: {references}. "
        "Ответ ограничен найденным контекстом и не включает неподтвержденные утверждения."
    )


def _build_confidence(citations: list[AiCitation]) -> float:
    if not citations:
        return 0.0
    return min(0.9, 0.3 + len(citations) * 0.1)


def ask_ai(payload: AiAskRequest, client: OpenSearch) -> AiAskResponse:
    trace_id = str(uuid4())
    query = _build_context_query(payload)

    try:
        raw = client.search(index=settings.opensearch_index, body=query)
    except Exception:
        return AiAskResponse(
            answer=(
                "Контекстный поиск временно недоступен. "
                "Проверьте доступность OpenSearch и повторите запрос."
            ),
            confidence=0.0,
            citations=[],
            source_policy=STRICT_SOURCE_POLICY,
            blocked=True,
            trace_id=trace_id,
            retrieval_stats={"retrieved_chunks": 0, "returned_citations": 0},
        )

    raw_hits = raw.get("hits", {}).get("hits", [])
    citations = _build_citations(raw_hits)

    if not citations:
        return AiAskResponse(
            answer=(
                "Ответ заблокирован политикой обязательных источников: "
                "для запроса не найдено подтвержденных цитат."
            ),
            confidence=0.0,
            citations=[],
            source_policy=STRICT_SOURCE_POLICY,
            blocked=True,
            trace_id=trace_id,
            retrieval_stats={"retrieved_chunks": len(raw_hits), "returned_citations": 0},
        )

    answer = _build_answer(payload, citations)
    confidence = _build_confidence(citations)

    return AiAskResponse(
        answer=answer,
        confidence=confidence,
        citations=citations,
        source_policy=STRICT_SOURCE_POLICY,
        blocked=False,
        trace_id=trace_id,
        retrieval_stats={"retrieved_chunks": len(raw_hits), "returned_citations": len(citations)},
    )
