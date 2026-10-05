"""FaceEmbeddingStore port.

Phase 1: in-app cosine over JSON vectors, **filtered by collection_id first**.
Scale path (HNSW / IVF-PQ / distributed shards) implements the same interface.
"""

from __future__ import annotations

import math
from typing import Any, Optional, Protocol
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.domain.models import FaceEmbedding


class FaceEmbeddingStore(Protocol):
    def insert(self, **kwargs) -> str: ...
    def batch_insert(self, items: list[dict]) -> int: ...
    def search(
        self,
        vector: list[float],
        collection_ids: list[UUID],
        top_k: int = 20,
        min_score: float = 0.0,
    ) -> list[dict]: ...
    def delete(self, embedding_id: UUID) -> None: ...
    def get(self, embedding_id: UUID) -> Optional[dict]: ...
    def count(self, collection_id: UUID) -> int: ...
    def create_index(self, collection_id: UUID) -> None: ...
    def rebuild_index(self, collection_id: UUID) -> None: ...
    def update_metadata(self, embedding_id: UUID, extra: dict) -> None: ...


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (na * nb)))


class InAppFaceStore:
    """Collection-partitioned cosine search. Never scans embeddings outside scope."""

    def __init__(self, db: Session):
        self.db = db

    def insert(self, **kwargs) -> str:
        row = FaceEmbedding(
            id=kwargs.get("id") or uuid4(),
            collection_id=kwargs["collection_id"],
            dataset_id=kwargs.get("dataset_id"),
            image_id=kwargs.get("image_id"),
            record_id=kwargs.get("record_id"),
            entity_id=kwargs.get("entity_id"),
            vector=list(kwargs["vector"]),
            dim=len(kwargs["vector"]),
            detector=kwargs.get("detector") or "phase1-perceptual",
            quality=float(kwargs.get("quality") or 0),
            extra=kwargs.get("extra") or {},
        )
        self.db.add(row)
        self.db.flush()
        return str(row.id)

    def batch_insert(self, items: list[dict]) -> int:
        n = 0
        for it in items:
            self.insert(**it)
            n += 1
        return n

    def search(
        self,
        vector: list[float],
        collection_ids: list[UUID],
        top_k: int = 20,
        min_score: float = 0.0,
    ) -> list[dict]:
        if not collection_ids:
            return []
        rows = (
            self.db.query(FaceEmbedding)
            .filter(FaceEmbedding.collection_id.in_(collection_ids))
            .all()
        )
        scored = []
        for r in rows:
            s = _cosine(vector, r.vector or [])
            if s < min_score:
                continue
            scored.append(
                {
                    "id": str(r.id),
                    "collection_id": str(r.collection_id),
                    "dataset_id": str(r.dataset_id) if r.dataset_id else None,
                    "image_id": str(r.image_id) if r.image_id else None,
                    "record_id": str(r.record_id) if r.record_id else None,
                    "entity_id": str(r.entity_id) if r.entity_id else None,
                    "score": round(s, 4),
                    "quality": r.quality,
                    "detector": r.detector,
                    "review": "human_required",
                    "identity_asserted": False,
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def delete(self, embedding_id: UUID) -> None:
        row = self.db.get(FaceEmbedding, embedding_id)
        if row:
            self.db.delete(row)

    def get(self, embedding_id: UUID) -> Optional[dict]:
        r = self.db.get(FaceEmbedding, embedding_id)
        if not r:
            return None
        return {"id": str(r.id), "collection_id": str(r.collection_id), "dim": r.dim}

    def count(self, collection_id: UUID) -> int:
        from sqlalchemy import func

        return self.db.query(func.count(FaceEmbedding.id)).filter(FaceEmbedding.collection_id == collection_id).scalar() or 0

    def create_index(self, collection_id: UUID) -> None:
        return None

    def rebuild_index(self, collection_id: UUID) -> None:
        return None

    def update_metadata(self, embedding_id: UUID, extra: dict[str, Any]) -> None:
        r = self.db.get(FaceEmbedding, embedding_id)
        if r:
            meta = dict(r.extra or {})
            meta.update(extra)
            r.extra = meta


def get_face_store(db: Session) -> InAppFaceStore:
    return InAppFaceStore(db)
