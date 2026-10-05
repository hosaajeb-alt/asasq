"""Kurdish (Arabic-script Sorani + Latin Kurmanji) matching folds."""

from __future__ import annotations

from app.normalization.persian import normalize_persian
from app.normalization.unicode_hygiene import hygiene

_SORANI = {
    "ێ": "ی",
    "ۆ": "و",
    "ڕ": "ر",
    "ڵ": "ل",
    "ە": "ه",
}


def normalize_kurdish(value: str) -> str:
    text = hygiene(value)
    if any(ord(ch) >= 0x0600 and ord(ch) <= 0x06FF for ch in text):
        text = "".join(_SORANI.get(ch, ch) for ch in text)
        return normalize_persian(text)
    return " ".join(text.lower().split())
