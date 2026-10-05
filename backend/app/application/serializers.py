from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID


def _v(val: Any) -> Any:
    if isinstance(val, UUID):
        return str(val)
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    return val


def user_out(u) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "display_name": u.display_name,
        "locale": u.locale,
        "role": u.role,
        "is_active": u.is_active,
        "last_login_at": _v(u.last_login_at),
        "created_at": _v(u.created_at),
    }


def dataset_out(d) -> dict:
    return {
        "id": str(d.id),
        "slug": d.slug,
        "name": d.name,
        "description": d.description,
        "category": d.category,
        "source": d.source,
        "source_description": d.source_description,
        "dataset_date": _v(d.dataset_date),
        "imported_at": _v(d.imported_at),
        "languages": d.languages or [],
        "geographic_scope": d.geographic_scope,
        "version_label": d.version_label,
        "legal_classification": d.legal_classification,
        "tags": d.tags or [],
        "notes": d.notes,
        "record_count": d.record_count,
        "processing_status": d.processing_status,
        "data_quality": d.data_quality or {},
        "schema": d.schema_json or {},
        "provenance": d.provenance or {},
        "owner_id": str(d.owner_id) if d.owner_id else None,
        "team_id": str(d.team_id) if d.team_id else None,
        "created_at": _v(d.created_at),
        "updated_at": _v(d.updated_at),
    }


def entity_out(e, extra: dict | None = None) -> dict:
    data = {
        "id": str(e.id),
        "canonical_name": e.canonical_name,
        "entity_type": e.entity_type,
        "confidence": e.confidence,
        "status": e.status,
        "merged_into_id": str(e.merged_into_id) if e.merged_into_id else None,
        "summary": e.summary,
        "tags": e.tags or [],
        "created_at": _v(e.created_at),
        "updated_at": _v(e.updated_at),
    }
    if extra:
        data.update(extra)
    return data


def investigation_out(c) -> dict:
    return {
        "id": str(c.id),
        "title": c.title,
        "summary": c.summary,
        "status": c.status,
        "classification": c.classification,
        "owner_id": str(c.owner_id) if c.owner_id else None,
        "team_id": str(c.team_id) if c.team_id else None,
        "tags": c.tags or [],
        "created_at": _v(c.created_at),
        "updated_at": _v(c.updated_at),
    }


def job_out(j) -> dict:
    return {
        "id": str(j.id),
        "dataset_id": str(j.dataset_id) if j.dataset_id else None,
        "filename": j.filename,
        "content_type": j.content_type,
        "byte_size": j.byte_size,
        "checksum": j.checksum,
        "status": j.status,
        "step": j.step,
        "records_processed": j.records_processed,
        "records_per_sec": j.records_per_sec,
        "error_count": j.error_count,
        "invalid_count": j.invalid_count,
        "duplicate_count": j.duplicate_count,
        "total_records": j.total_records,
        "started_at": _v(j.started_at),
        "finished_at": _v(j.finished_at),
        "error_message": j.error_message,
        "wizard_state": j.wizard_state or {},
        "created_at": _v(j.created_at),
    }
