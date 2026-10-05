"""Russian / Cyrillic matching. ё → е is a matching fold, not a spelling change."""

from __future__ import annotations

from app.normalization.unicode_hygiene import hygiene


def normalize_russian(value: str) -> str:
    text = hygiene(value)
    text = text.replace("Ё", "Е").replace("ё", "е")
    text = text.casefold()
    return " ".join(text.split())
