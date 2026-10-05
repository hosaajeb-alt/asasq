"""Commit an approved import: stream rows → records + values + search docs + entities."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.application.parsers import iter_rows
from app.domain.models import (
    Dataset,
    DatasetField,
    DatasetVersion,
    Entity,
    EntityAlias,
    EntityAttribute,
    EntityRecordLink,
    Record,
    RecordValue,
    SearchDoc,
)
from app.normalization.engine import NormalizationEngine


def _hash_row(row: dict[str, Any]) -> str:
    blob = "|".join(f"{k}={row.get(k, '')}" for k in sorted(row.keys()))
    return hashlib.sha256(blob.encode("utf-8", errors="replace")).hexdigest()


def commit_import(
    db: Session,
    *,
    dataset: Dataset,
    version: DatasetVersion,
    storage_path: str,
    filename: str,
    content_type: str,
    schema_fields: list[dict[str, Any]],
    language_hint: str | None,
    entity_mappings: dict[str, str] | None = None,
) -> dict[str, Any]:
    engine = NormalizationEngine()
    entity_mappings = entity_mappings or {}
    seen_hash: dict[str, UUID] = {}
    # name-type -> entity
    entity_index: dict[tuple[str, str], Entity] = {}
    processed = 0
    invalid = 0
    duplicates = 0
    now = datetime.now(timezone.utc)

    field_by_name = {f["name"]: f for f in schema_fields}

    for row_number, row in enumerate(iter_rows(storage_path, filename, content_type), start=1):
        h = _hash_row(row)
        rec = Record(
            dataset_id=dataset.id,
            version_id=version.id,
            row_number=row_number,
            raw_payload=row,
            language=language_hint or "",
            content_hash=h,
        )
        if h in seen_hash:
            rec.duplicate_of = seen_hash[h]
            rec.duplicate_confidence = 1.0
            rec.duplicate_reason = "exact"
            duplicates += 1
        else:
            seen_hash[h] = rec.id
        db.add(rec)
        db.flush()

        attrs: dict[str, Any] = {}
        person_name = None
        org_name = None
        primary_lang = language_hint or ""

        for name, raw in row.items():
            meta = field_by_name.get(name) or {"semantic_type": "FreeText", "name": name}
            st = meta.get("semantic_type") or "FreeText"
            env = engine.normalize(raw, st, language_hint)
            if raw not in (None, "") and not env.is_valid:
                invalid += 1
            keys = engine.block_keys(env, st)
            db.add(
                RecordValue(
                    record_id=rec.id,
                    dataset_id=dataset.id,
                    field_name=name,
                    semantic_type=st,
                    original_value=env.original_value,
                    normalized_value=env.normalized_value,
                    canonical_value=env.canonical_value,
                    transliterated_value=env.transliterated_value,
                    phonetic_value=env.phonetic_value,
                    language=env.language,
                    script=env.script,
                    is_valid=env.is_valid,
                    block_keys=keys,
                )
            )
            if env.original_value:
                db.add(
                    SearchDoc(
                        dataset_id=dataset.id,
                        record_id=rec.id,
                        semantic_type=st,
                        field_name=name,
                        original_text=env.original_value,
                        normalized_text=env.normalized_value,
                        canonical_text=env.canonical_value,
                        transliteration=env.transliterated_value,
                        phonetic_key=env.phonetic_value,
                        language=env.language,
                        script=env.script,
                        classification=dataset.legal_classification,
                    )
                )
            attrs[st] = env.as_dict()
            if st == "PersonName" and env.normalized_value:
                person_name = env
            if st == "OrganizationName" and env.normalized_value:
                org_name = env
            if env.language:
                primary_lang = env.language

        # Lightweight per-record entity (not a merge). ER proposes later.
        target = None
        etype = None
        if person_name and entity_mappings.get("PersonName", "person") == "person":
            target, etype = person_name, "person"
        elif org_name:
            target, etype = org_name, "organization"
        if target and etype:
            key = (etype, target.canonical_value.lower())
            ent = entity_index.get(key)
            if ent is None:
                ent = Entity(
                    canonical_name=target.normalized_value or target.original_value,
                    entity_type=etype,
                    confidence=0.55,
                    status="active",
                    summary="",
                )
                db.add(ent)
                db.flush()
                entity_index[key] = ent
                if target.original_value and target.original_value != ent.canonical_name:
                    db.add(EntityAlias(entity_id=ent.id, alias=target.original_value, script=target.script, source="original"))
                if target.transliterated_value:
                    for alias in target.transliterated_value.split("|"):
                        alias = alias.strip()
                        if alias:
                            db.add(EntityAlias(entity_id=ent.id, alias=alias, script="Latn", source="transliteration"))
            db.add(
                EntityRecordLink(
                    entity_id=ent.id,
                    record_id=rec.id,
                    dataset_id=dataset.id,
                    match_confidence=1.0,
                    explain_json={"reason": "same canonical name on ingest (not identity proof)"},
                )
            )
            for st, envd in attrs.items():
                val = envd.get("original_value")
                if not val:
                    continue
                db.add(
                    EntityAttribute(
                        entity_id=ent.id,
                        name=st,
                        value=val,
                        semantic_type=st,
                        origin="observed",
                        record_id=rec.id,
                        dataset_id=dataset.id,
                    )
                )
            db.query(SearchDoc).filter(SearchDoc.record_id == rec.id).update(
                {"entity_id": ent.id, "entity_type": etype}
            )

        processed += 1
        if processed % 500 == 0:
            db.flush()

    dataset.record_count = processed
    dataset.processing_status = "ready"
    dataset.imported_at = now
    version.record_count = processed
    db.flush()
    return {
        "records_processed": processed,
        "invalid_count": invalid,
        "duplicate_count": duplicates,
        "entities_created": len(entity_index),
    }
