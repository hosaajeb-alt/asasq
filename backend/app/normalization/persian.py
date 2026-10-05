"""Persian (Farsi) normalization.

Matching form folds letter variants and strips marks. The original string is
never mutated by the caller — this module only returns a derived form.
"""

from __future__ import annotations

import unicodedata

from app.normalization.unicode_hygiene import hygiene, strip_combining

# Presentation-form ranges folded via NFKC for matching only.
TATWEEL = "\u0640"
ZWNJ = "\u200c"
ZWSP = "\u200b"

_LETTER_MAP = {
    "ي": "ی",  # Arabic yeh → Persian yeh
    "ى": "ی",  # alef maksura
    "ئ": "ی",  # yeh with hamza — matching fold
    "ك": "ک",  # Arabic kaf → Persian keheh
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ٱ": "ا",
    "ة": "ه",
    "ۀ": "ه",
    "ؤ": "و",
    "ء": "",
    "ڪ": "ک",
    "ے": "ی",
}


def normalize_persian(value: str, *, keep_zwnj: bool = False) -> str:
    text = hygiene(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(TATWEEL, "")
    text = text.replace(ZWSP, "")
    if not keep_zwnj:
        text = text.replace(ZWNJ, " ")
    text = strip_combining(text)  # harakat / madda as combining
    # Explicit Arabic diacritics that sometimes survive as letters
    for mark in "ًٌٍَُِّْٕٖٓٔٗ٘":
        text = text.replace(mark, "")
    text = "".join(_LETTER_MAP.get(ch, ch) for ch in text)
    text = " ".join(text.split())
    return text


def canonical_persian_name(value: str) -> str:
    return normalize_persian(value)
