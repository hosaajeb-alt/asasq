"""Hebrew: fold final forms, strip niqqud for matching."""

from __future__ import annotations

from app.normalization.unicode_hygiene import hygiene, strip_combining

_FINAL = {
    "ך": "כ",
    "ם": "מ",
    "ן": "נ",
    "ף": "פ",
    "ץ": "צ",
}


def normalize_hebrew(value: str) -> str:
    text = hygiene(value)
    text = strip_combining(text)  # niqqud
    text = "".join(_FINAL.get(ch, ch) for ch in text)
    return " ".join(text.split())
