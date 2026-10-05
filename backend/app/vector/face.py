"""Face pipeline (Phase 1).

Real detectors/aligners plug in behind the same steps. Identity is never asserted.
"""

from __future__ import annotations

import hashlib
from typing import Any


def quality_score(data: bytes) -> float:
    if not data:
        return 0.0
    # Size as a coarse stand-in; production uses blur / pose / det-score.
    n = len(data)
    if n < 64:
        return 0.2
    if n < 2048:
        return 0.55
    return min(0.95, 0.6 + min(n, 200_000) / 400_000)


def embed_bytes(data: bytes, dim: int = 64) -> list[float]:
    """Deterministic perceptual-ish vector. Not a biometric model."""
    vec: list[float] = []
    buf = data or b"\x00"
    while len(vec) < dim:
        buf = hashlib.sha256(buf).digest()
        for b in buf:
            vec.append((b / 127.5) - 1.0)
            if len(vec) >= dim:
                break
    return vec[:dim]


def embed_seed(seed: str, dim: int = 64) -> list[float]:
    return embed_bytes(seed.encode("utf-8"), dim)


def run_pipeline(image_bytes: bytes) -> dict[str, Any]:
    q = quality_score(image_bytes)
    return {
        "detected": True,
        "quality": q,
        "aligned": True,
        "vector": embed_bytes(image_bytes),
        "detector": "phase1-perceptual",
        "identity_asserted": False,
        "note": "Candidate only — human review required. Similarity is not identity.",
    }
