from __future__ import annotations

import unicodedata

from app.normalization.unicode_hygiene import hygiene


def normalize_english(value: str) -> str:
    text = hygiene(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("’", "'").replace("`", "'")
    text = " ".join(text.split())
    return text


def canonical_english_name(value: str) -> str:
    return normalize_english(value).casefold()
