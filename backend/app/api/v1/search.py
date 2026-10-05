from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.application.audit import write_audit
from app.domain.models import Dataset, Entity, Record, SearchDoc, User
from app.infrastructure.db import get_db
from app.normalization.engine import NormalizationEngine
from app.search.ranking import MatchSignals, RANKING_PRESETS, rank_score

router = APIRouter(prefix="/search", tags=["search"])


class SearchIn(BaseModel):
    q: str
    mode: str = "balanced"
    entity_type: Optional[str] = None
    dataset_id: Optional[str] = None
    language: Optional[str] = None
    semantic_type: Optional[str] = None
    page: int = 1
    page_size: int = 25


def _signals(q_env, doc: SearchDoc, mode: str) -> MatchSignals:
    q_orig = q_env.original_value.strip()
    q_norm = (q_env.normalized_value or "").lower()
    q_canon = (q_env.canonical_value or "").lower()
    q_ph = q_env.phonetic_value or ""
    q_tr = [t.strip().lower() for t in (q_env.transliterated_value or "").split("|") if t.strip()]

    orig = doc.original_text or ""
    norm = (doc.normalized_text or "").lower()
    canon = (doc.canonical_text or "").lower()
    tr = (doc.transliteration or "").lower()
    ph = doc.phonetic_key or ""

    exact = 1.0 if orig == q_orig or orig.lower() == q_orig.lower() else 0.0
    normalized = 0.0
    if q_canon and canon and q_canon == canon:
        normalized = 1.0
    elif q_norm and norm and q_norm == norm:
        normalized = 0.92
    elif q_norm and norm and (q_norm in norm or norm in q_norm):
        normalized = 0.7
    transliteration = 0.0
    if q_tr and tr:
        if any(t and t in tr for t in q_tr):
            transliteration = 0.9
        elif q_orig.lower() in tr:
            transliteration = 0.85
    phonetic = 1.0 if q_ph and ph and q_ph == ph else 0.0
    return MatchSignals(
        exact=exact,
        normalized=normalized,
        transliteration=transliteration,
        phonetic=phonetic,
        attribute=1.0 if exact or normalized >= 0.92 else 0.0,
        context=0.2 if doc.entity_id else 0.0,
        source=doc.source_confidence or 1.0,
    )


@router.post("")
def search(
    body: SearchIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = body.q.strip()
    if not q:
        return {"total": 0, "items": [], "expanded": {}, "mode": body.mode}
    engine = NormalizationEngine()
    env = engine.normalize(q, "PersonName")
    env_email = engine.normalize(q, "Email")
    expanded = {
        "original": q,
        "normalized": env.normalized_value,
        "canonical": env.canonical_value,
        "transliteration": env.transliterated_value,
        "phonetic": env.phonetic_value,
        "language": env.language,
        "script": env.script,
        "email_canonical": env_email.canonical_value if env_email.is_valid else None,
    }
    terms = {q, env.normalized_value, env.canonical_value}
    for t in (env.transliterated_value or "").split("|"):
        if t.strip():
            terms.add(t.strip())
    terms = {t for t in terms if t}

    query = db.query(SearchDoc)
    if body.dataset_id:
        query = query.filter(SearchDoc.dataset_id == body.dataset_id)
    if body.entity_type:
        query = query.filter(SearchDoc.entity_type == body.entity_type)
    if body.language:
        query = query.filter(SearchDoc.language == body.language)
    if body.semantic_type:
        query = query.filter(SearchDoc.semantic_type == body.semantic_type)

    clauses = []
    for t in list(terms)[:8]:
        like = f"%{t}%"
        clauses.append(SearchDoc.original_text.ilike(like))
        clauses.append(SearchDoc.normalized_text.ilike(like))
        clauses.append(SearchDoc.canonical_text.ilike(like))
        clauses.append(SearchDoc.transliteration.ilike(like))
    if env.phonetic_value:
        clauses.append(SearchDoc.phonetic_key == env.phonetic_value)
    if env_email.is_valid:
        clauses.append(SearchDoc.canonical_text == env_email.canonical_value)
    query = query.filter(or_(*clauses))
    docs = query.limit(400).all()

    # collapse by record
    best: dict[str, dict] = {}
    mode = body.mode if body.mode in RANKING_PRESETS else "balanced"
    cutoff = RANKING_PRESETS[mode]["fuzzy_cutoff"]
    ds_cache: dict = {}
    rec_cache: dict = {}
    ent_cache: dict = {}

    for doc in docs:
        sig = _signals(env, doc, mode)
        # also try email envelope if query looks like email
        if env_email.is_valid:
            sig_e = _signals(env_email, doc, mode)
            if sig_e.exact + sig_e.normalized > sig.exact + sig.normalized:
                sig = sig_e
        score, why = rank_score(sig, mode)
        strong = sig.exact >= 1 or sig.normalized >= 0.7 or sig.transliteration >= 0.8 or sig.phonetic >= 1
        if not strong and score < cutoff * 0.35:
            continue
        rid = str(doc.record_id)
        prev = best.get(rid)
        if prev and prev["score"] >= score:
            continue
        ds = ds_cache.get(doc.dataset_id)
        if ds is None:
            ds = db.get(Dataset, doc.dataset_id)
            ds_cache[doc.dataset_id] = ds
        rec = rec_cache.get(doc.record_id)
        if rec is None:
            rec = db.get(Record, doc.record_id)
            rec_cache[doc.record_id] = rec
        ent = None
        if doc.entity_id:
            ent = ent_cache.get(doc.entity_id)
            if ent is None:
                ent = db.get(Entity, doc.entity_id)
                ent_cache[doc.entity_id] = ent
        match_type = why[0] if why else "partial"
        best[rid] = {
            "record_id": rid,
            "entity_id": str(doc.entity_id) if doc.entity_id else None,
            "entity_name": ent.canonical_name if ent else (doc.original_text or ""),
            "entity_type": (ent.entity_type if ent else doc.entity_type) or "",
            "dataset_id": str(doc.dataset_id),
            "dataset_name": ds.name if ds else "",
            "field_name": doc.field_name,
            "semantic_type": doc.semantic_type,
            "original": doc.original_text,
            "normalized": doc.normalized_text,
            "transliteration": doc.transliteration,
            "language": doc.language,
            "script": doc.script,
            "raw": rec.raw_payload if rec else {},
            "score": score,
            "confidence": score,
            "match_type": match_type,
            "explain": why,
            "signals": {
                "exact": sig.exact,
                "normalized": sig.normalized,
                "transliteration": sig.transliteration,
                "phonetic": sig.phonetic,
            },
        }

    items = sorted(best.values(), key=lambda x: x["score"], reverse=True)
    total = len(items)
    start = (body.page - 1) * body.page_size
    page_items = items[start : start + body.page_size]
    write_audit(
        db,
        actor_id=user.id,
        action="search",
        resource_type="search",
        payload={"q": q, "mode": mode, "hits": total},
        ip=request.client.host if request.client else "",
    )
    db.commit()
    return {
        "total": total,
        "page": body.page,
        "page_size": body.page_size,
        "mode": mode,
        "weights": {k: v for k, v in RANKING_PRESETS[mode].items() if k != "fuzzy_cutoff"},
        "expanded": expanded,
        "items": page_items,
    }


@router.get("/suggest")
def suggest(q: str = Query(""), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = q.strip()
    if len(q) < 2:
        return {"items": []}
    like = f"{q}%"
    docs = (
        db.query(SearchDoc)
        .filter(
            or_(
                SearchDoc.original_text.ilike(like),
                SearchDoc.normalized_text.ilike(like),
                SearchDoc.transliteration.ilike(f"%{q}%"),
            )
        )
        .limit(12)
        .all()
    )
    seen = set()
    items = []
    for d in docs:
        key = d.original_text
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "text": d.original_text,
                "normalized": d.normalized_text,
                "semantic_type": d.semantic_type,
                "entity_type": d.entity_type,
            }
        )
    return {"items": items}
