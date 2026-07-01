from __future__ import annotations

import json
from urllib.parse import quote_plus
from urllib.request import urlopen
from uuid import uuid4

from opensearchpy import OpenSearch

from app.config import settings
from app.schemas import AiAskRequest, AiAskResponse, AiCitation


STRICT_SOURCE_POLICY = "strict-required-citations"
INTERNET_SOURCE_POLICY = "internet-best-effort"


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


def _extract_related_topic(data: dict) -> tuple[str, str]:
    related = data.get("RelatedTopics") or []
    if not isinstance(related, list):
        return "", ""

    for item in related:
        if not isinstance(item, dict):
            continue

        text = str(item.get("Text") or "").strip()
        url = str(item.get("FirstURL") or "").strip()
        if text:
            return text, url

        nested = item.get("Topics") or []
        if isinstance(nested, list):
            for nested_item in nested:
                if not isinstance(nested_item, dict):
                    continue
                nested_text = str(nested_item.get("Text") or "").strip()
                nested_url = str(nested_item.get("FirstURL") or "").strip()
                if nested_text:
                    return nested_text, nested_url

    return "", ""


def _internet_query_candidates(question: str) -> list[str]:
    base = question.strip()
    if not base:
        return [question]

    lowered = base.lower()
    prefixes = [
        "что такое ",
        "что это ",
        "what is ",
        "what are ",
    ]

    candidates = [base]
    for prefix in prefixes:
        if lowered.startswith(prefix):
            trimmed = base[len(prefix):].strip(" ?!.,")
            if trimmed:
                candidates.append(trimmed)
            break

    dedup: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        dedup.append(candidate)
    return dedup


def _ask_google_search_api(payload: AiAskRequest, trace_id: str) -> AiAskResponse | None:
    api_key = settings.google_search_api_key.strip()
    cx = settings.google_search_cx.strip()
    if not api_key or not cx:
        return None

    endpoint = (
        "https://www.googleapis.com/customsearch/v1?"
        f"key={quote_plus(api_key)}&cx={quote_plus(cx)}&q={quote_plus(payload.question)}&num=3&hl=ru"
    )
    try:
        with urlopen(endpoint, timeout=8) as response:  # nosec B310
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        return None

    citations: list[AiCitation] = []
    for item in items[:3]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "Google result").strip()
        link = str(item.get("link") or "").strip()
        snippet = str(item.get("snippet") or "").strip()
        if not link:
            continue
        citations.append(
            AiCitation(
                doc_id=link,
                chunk_id="internet:google-cse",
                title=title,
                snippet=(snippet or title)[:240],
            )
        )

    if not citations:
        return None

    top_titles = "; ".join(citation.title for citation in citations)
    answer = (
        f"Интернет-результаты по запросу '{payload.question}' (Google, топ-{len(citations)}): "
        f"{top_titles}. Откройте источники ниже для деталей."
    )
    return AiAskResponse(
        answer=answer,
        confidence=0.7,
        citations=citations,
        source_policy=INTERNET_SOURCE_POLICY,
        blocked=False,
        trace_id=trace_id,
        retrieval_stats={"retrieved_chunks": len(citations), "returned_citations": len(citations)},
    )


def _ask_ai_internet(payload: AiAskRequest, trace_id: str) -> AiAskResponse:
    google_response = _ask_google_search_api(payload, trace_id)
    if google_response is not None:
        return google_response

    abstract_text = ""
    abstract_url = ""
    heading = "DuckDuckGo"
    had_network_error = False

    for candidate_query in _internet_query_candidates(payload.question):
        endpoint = (
            "https://api.duckduckgo.com/?q="
            f"{quote_plus(candidate_query)}"
            "&format=json&no_redirect=1&no_html=1"
        )
        try:
            with urlopen(endpoint, timeout=8) as response:  # nosec B310
                data = json.loads(response.read().decode("utf-8"))
        except Exception:
            had_network_error = True
            continue

        heading = str(data.get("Heading") or heading)
        abstract_text = str(data.get("AbstractText") or "").strip()
        abstract_url = str(data.get("AbstractURL") or "").strip()

        if not abstract_text:
            related_text, related_url = _extract_related_topic(data)
            if related_text:
                abstract_text = related_text
                if not abstract_url:
                    abstract_url = related_url

        if not abstract_text and abstract_url:
            abstract_text = (
                f"Для запроса найден внешний источник '{heading}'. "
                "Откройте ссылку для подробного описания."
            )

        if abstract_text:
            break

    if had_network_error and not abstract_text:
        return AiAskResponse(
            answer=(
                "Интернет-поиск временно недоступен. "
                "Проверьте сетевое подключение и повторите запрос."
            ),
            confidence=0.0,
            citations=[],
            source_policy=INTERNET_SOURCE_POLICY,
            blocked=True,
            trace_id=trace_id,
            retrieval_stats={"retrieved_chunks": 0, "returned_citations": 0},
        )

    if not abstract_text:
        yandex_url = f"https://yandex.ru/search/?text={quote_plus(payload.question)}"
        return AiAskResponse(
            answer=(
                "Для этого интернет-запроса не найден короткий подтвержденный summary. "
                "Откройте результаты поиска в Yandex по ссылке из источников."
            ),
            confidence=0.2,
            citations=[
                AiCitation(
                    doc_id=yandex_url,
                    chunk_id="internet:yandex-search",
                    title="Yandex search",
                    snippet=f"Поиск в интернете по запросу: {payload.question}",
                )
            ],
            source_policy=INTERNET_SOURCE_POLICY,
            blocked=False,
            trace_id=trace_id,
            retrieval_stats={"retrieved_chunks": 1, "returned_citations": 1},
        )

    citations = [
        AiCitation(
            doc_id=abstract_url or "internet:duckduckgo",
            chunk_id="internet:summary",
            title=heading or "Internet source",
            snippet=abstract_text[:240],
        )
    ]

    source_line = f"Источник: {abstract_url}." if abstract_url else "Источник: DuckDuckGo Instant Answer."
    answer = f"Интернет-ответ по запросу '{payload.question}': {abstract_text}\n\n{source_line}"
    return AiAskResponse(
        answer=answer,
        confidence=0.65,
        citations=citations,
        source_policy=INTERNET_SOURCE_POLICY,
        blocked=False,
        trace_id=trace_id,
        retrieval_stats={"retrieved_chunks": 1, "returned_citations": 1},
    )


def ask_ai(payload: AiAskRequest, client: OpenSearch) -> AiAskResponse:
    trace_id = str(uuid4())

    if payload.source_scope == "internet":
        return _ask_ai_internet(payload, trace_id)

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
