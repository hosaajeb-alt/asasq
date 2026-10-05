from __future__ import annotations

from collections import defaultdict
from typing import Iterable


def generate_candidates(records: Iterable[dict]) -> list[tuple[str, str, str]]:
    """Return (id_a, id_b, shared_block_key) without O(n²).

    Each record: {id, block_keys: [str]}
    """
    inverted: dict[str, list[str]] = defaultdict(list)
    for rec in records:
        rid = rec["id"]
        for key in set(rec.get("block_keys") or []):
            inverted[key].append(rid)

    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str, str]] = []
    for key, ids in inverted.items():
        if len(ids) < 2 or len(ids) > 500:
            # skip huge blocks (e.g. empty names) — they explode
            continue
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                edge = (a, b) if a < b else (b, a)
                if edge in seen:
                    continue
                seen.add(edge)
                pairs.append((edge[0], edge[1], key))
    return pairs
