from __future__ import annotations

import json
from pathlib import Path

from app.schemas import GlossaryEntry, GlossaryEntryWriteRequest
from app.services.storage_service import (
    replace_glossary_entries_storage,
    glossary_entries_count,
    list_glossary_entries_storage,
    save_glossary_entry_storage,
    delete_glossary_entry_storage,
)


def _glossary_path() -> Path:
    return Path(__file__).resolve().parent.parent / "static" / "glossary.json"


def _default_payload() -> dict:
    return {"entries": []}


def _read_payload() -> dict:
    path = _glossary_path()
    if not path.exists():
        return _default_payload()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("glossary.json contains invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("glossary.json must contain an object")
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("glossary.json field 'entries' must be a list")
    return {"entries": entries}


def _write_payload(payload: dict) -> None:
    path = _glossary_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _seed_storage_from_json_if_needed() -> None:
    if glossary_entries_count() > 0:
        return
    payload = _read_payload()
    entries = [GlossaryEntry(**item) for item in payload.get("entries", [])]
    for entry in entries:
        save_glossary_entry_storage(entry)


def list_glossary_entries() -> list[GlossaryEntry]:
    _seed_storage_from_json_if_needed()
    return list_glossary_entries_storage()


def create_glossary_entry(payload: GlossaryEntryWriteRequest) -> GlossaryEntry:
    _seed_storage_from_json_if_needed()
    entries = list_glossary_entries_storage()
    normalized_abbr = payload.abbr.strip()
    if any(item.abbr.strip().lower() == normalized_abbr.lower() for item in entries):
        raise ValueError("Glossary entry already exists")
    entry_payload = payload.model_dump(exclude_none=True)
    entry_payload["abbr"] = normalized_abbr
    entry = GlossaryEntry(**entry_payload)
    save_glossary_entry_storage(entry)
    return entry


def update_glossary_entry(abbr: str, payload: GlossaryEntryWriteRequest) -> GlossaryEntry:
    _seed_storage_from_json_if_needed()
    entries = list_glossary_entries_storage()
    normalized_path_abbr = abbr.strip().lower()
    normalized_next_abbr = payload.abbr.strip()

    index = next(
        (idx for idx, item in enumerate(entries) if item.abbr.strip().lower() == normalized_path_abbr),
        None,
    )
    if index is None:
        raise ValueError("Glossary entry not found")

    if normalized_next_abbr.lower() != normalized_path_abbr and any(
        item.abbr.strip().lower() == normalized_next_abbr.lower() for idx, item in enumerate(entries) if idx != index
    ):
        raise ValueError("Glossary entry already exists")

    entry_payload = payload.model_dump(exclude_none=True)
    entry_payload["abbr"] = normalized_next_abbr
    entry = GlossaryEntry(**entry_payload)
    if normalized_next_abbr.lower() != normalized_path_abbr:
        delete_glossary_entry_storage(abbr)
    save_glossary_entry_storage(entry)
    return entry


def delete_glossary_entry(abbr: str) -> bool:
    _seed_storage_from_json_if_needed()
    return delete_glossary_entry_storage(abbr)


def export_glossary_entries() -> list[GlossaryEntry]:
    _seed_storage_from_json_if_needed()
    return list_glossary_entries_storage()


def import_glossary_entries(entries: list[GlossaryEntryWriteRequest], replace_existing: bool = True) -> list[GlossaryEntry]:
    _seed_storage_from_json_if_needed()
    normalized_entries: list[GlossaryEntry] = []
    seen: set[str] = set()
    for payload in entries:
        normalized_abbr = payload.abbr.strip()
        key = normalized_abbr.lower()
        if key in seen:
            raise ValueError("Glossary import contains duplicate abbreviations")
        seen.add(key)
        entry_payload = payload.model_dump(exclude_none=True)
        entry_payload["abbr"] = normalized_abbr
        normalized_entries.append(GlossaryEntry(**entry_payload))

    if replace_existing:
        replace_glossary_entries_storage(normalized_entries)
    else:
        existing = {item.abbr.lower() for item in list_glossary_entries_storage()}
        for entry in normalized_entries:
            if entry.abbr.lower() in existing:
                raise ValueError(f"Glossary entry already exists: {entry.abbr}")
            save_glossary_entry_storage(entry)
            existing.add(entry.abbr.lower())

    return list_glossary_entries_storage()