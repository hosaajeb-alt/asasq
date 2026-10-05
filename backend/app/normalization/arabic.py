"""Arabic normalization — Arabic yeh/kaf defaults, not Persian ones."""

from __future__ import annotations

import unicodedata

from app.normalization.unicode_hygiene import hygiene, strip_combining

TATWEEL = "\u0640"

_LETTER_MAP = {
    "ی": "ي",  # Persian yeh → Arabic yeh for Arabic-language matching
    "ى": "ي",
    "ک": "ك",
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ٱ": "ا",
    "ة": "ه",
    "ؤ": "و",
    "ء": "",
}


def normalize_arabic(value: str) -> str:
    text = hygiene(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(TATWEEL, "")
    text = text.replace("\u200c", " ").replace("\u200b", "")
    text = strip_combining(text)
    for mark in "ًٌٍَُِّْٕٖٓٔٗ٘":
        text = text.replace(mark, "")
    text = "".join(_LETTER_MAP.get(ch, ch) for ch in text)
    return " ".join(text.split())
