"""Phonetic keys as ranking signals — never proof of identity."""

from __future__ import annotations

import re

_VOWELS_LATIN = re.compile(r"[aeiouyhw]+", re.I)

# Persian/Arabic consonants kept as a skeleton (already-normalized input).
_FA_CONS = {
    "ب": "B",
    "پ": "P",
    "ت": "T",
    "ط": "T",
    "د": "D",
    "ک": "K",
    "ك": "K",
    "گ": "G",
    "ق": "Q",
    "ف": "F",
    "س": "S",
    "ص": "S",
    "ث": "S",
    "ز": "Z",
    "ذ": "Z",
    "ض": "Z",
    "ظ": "Z",
    "ش": "X",
    "ژ": "J",
    "ج": "J",
    "چ": "C",
    "ل": "L",
    "م": "M",
    "ن": "N",
    "ر": "R",
    "و": "V",
    "ه": "H",
    "ح": "H",
    "ی": "Y",
    "ي": "Y",
    "خ": "H",
    "غ": "G",
}


def latin_phonetic(value: str) -> str:
    """Simplified metaphone-like key for Latin script."""
    text = re.sub(r"[^a-z]", "", value.lower())
    if not text:
        return ""
    text = text.replace("ph", "f").replace("kn", "n").replace("wr", "r")
    text = text.replace("sch", "sk").replace("ch", "x").replace("sh", "x")
    text = text.replace("zh", "j").replace("gh", "g").replace("kh", "k")
    text = _VOWELS_LATIN.sub("", text[0] + text[1:]) if len(text) > 1 else text
    # collapse repeats
    out = []
    for ch in text.upper():
        if not out or out[-1] != ch:
            out.append(ch)
    return "".join(out)[:8]


def arabic_script_phonetic(value: str) -> str:
    out = []
    for ch in value:
        if ch in _FA_CONS:
            k = _FA_CONS[ch]
            if not out or out[-1] != k:
                out.append(k)
    return "".join(out)[:10]


def phonetic_key(value: str, script: str = "") -> str:
    if script == "Arab" or any("\u0600" <= ch <= "\u06FF" for ch in value):
        return arabic_script_phonetic(value)
    return latin_phonetic(value)
