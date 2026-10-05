"""Turkish locale-correct case folding (İ/I/i/ı)."""

from __future__ import annotations

from app.normalization.unicode_hygiene import hygiene


def casefold_turkish(value: str) -> str:
    text = hygiene(value)
    # Order matters: dotted/dotless I must be handled before generic lower().
    text = text.replace("İ", "i").replace("I", "ı")
    text = text.lower()
    # lower() of 'I' on a non-tr locale would have become 'i'; we already mapped.
    return " ".join(text.split())


def normalize_turkish(value: str) -> str:
    return casefold_turkish(value)
