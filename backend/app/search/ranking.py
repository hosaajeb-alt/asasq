from __future__ import annotations

from dataclasses import dataclass

RANKING_PRESETS = {
    "exact": {
        "exact": 1.0,
        "normalized": 0.15,
        "transliteration": 0.0,
        "phonetic": 0.0,
        "attribute": 0.2,
        "context": 0.1,
        "source": 0.05,
        "fuzzy_cutoff": 1.0,
    },
    "high_precision": {
        "exact": 0.7,
        "normalized": 0.5,
        "transliteration": 0.25,
        "phonetic": 0.05,
        "attribute": 0.2,
        "context": 0.1,
        "source": 0.05,
        "fuzzy_cutoff": 0.92,
    },
    "balanced": {
        "exact": 0.55,
        "normalized": 0.45,
        "transliteration": 0.35,
        "phonetic": 0.15,
        "attribute": 0.2,
        "context": 0.1,
        "source": 0.08,
        "fuzzy_cutoff": 0.78,
    },
    "broad": {
        "exact": 0.4,
        "normalized": 0.4,
        "transliteration": 0.4,
        "phonetic": 0.3,
        "attribute": 0.15,
        "context": 0.1,
        "source": 0.05,
        "fuzzy_cutoff": 0.62,
    },
}


@dataclass
class MatchSignals:
    exact: float = 0.0
    normalized: float = 0.0
    transliteration: float = 0.0
    phonetic: float = 0.0
    attribute: float = 0.0
    context: float = 0.0
    source: float = 1.0


def rank_score(signals: MatchSignals, mode: str = "balanced", weights: dict | None = None) -> tuple[float, list[str]]:
    w = dict(weights or RANKING_PRESETS.get(mode, RANKING_PRESETS["balanced"]))
    score = (
        w["exact"] * signals.exact
        + w["normalized"] * signals.normalized
        + w["transliteration"] * signals.transliteration
        + w["phonetic"] * signals.phonetic
        + w["attribute"] * signals.attribute
        + w["context"] * signals.context
        + w["source"] * signals.source
    )
    # normalize roughly to 0-1 by sum of weights
    denom = sum(v for k, v in w.items() if k != "fuzzy_cutoff") or 1.0
    score = min(1.0, score / denom * 1.15)
    if signals.exact >= 0.99:
        score = max(score, 0.95)
    elif signals.normalized >= 0.9:
        score = max(score, 0.82)
    elif signals.transliteration >= 0.8:
        score = max(score, 0.64)
    why = []
    if signals.exact >= 0.99:
        why.append("exact match")
    if signals.normalized >= 0.8:
        why.append("normalized match")
    if signals.transliteration >= 0.8:
        why.append("transliteration match")
    if signals.phonetic >= 0.99:
        why.append("phonetic key")
    if signals.attribute >= 0.8:
        why.append("attribute match")
    if not why:
        why.append("partial / fuzzy")
    return round(score, 4), why
