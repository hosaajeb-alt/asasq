from __future__ import annotations

from typing import Any

from app.entity_resolution.blocking import generate_candidates
from app.entity_resolution.scoring import score_pair


class EntityResolutionEngine:
    def propose(self, records: list[dict[str, Any]], min_confidence: float = 0.55) -> list[dict[str, Any]]:
        """records: {id, block_keys, attributes: {semantic_type: envelope-dict}}"""
        by_id = {r["id"]: r for r in records}
        pairs = generate_candidates(records)
        proposals = []
        for a, b, key in pairs:
            explain = score_pair(by_id[a].get("attributes") or {}, by_id[b].get("attributes") or {})
            if explain.confidence < min_confidence:
                continue
            proposals.append(
                {
                    "record_a": a,
                    "record_b": b,
                    "block_key": key,
                    "confidence": explain.confidence,
                    "reasons": explain.reasons,
                    "components": explain.components,
                    "auto_link_eligible": explain.auto_link_eligible,
                    "status": "proposed",
                }
            )
        proposals.sort(key=lambda p: p["confidence"], reverse=True)
        return proposals
