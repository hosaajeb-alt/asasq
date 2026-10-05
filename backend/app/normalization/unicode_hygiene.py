"""Shared Unicode hygiene — NOT a substitute for language modules."""

from __future__ import annotations

import re
import unicodedata

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MULTI_SPACE = re.compile(r"[ \t\f\v]+")


def hygiene(value: str) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFC", str(value))
    text = _CONTROL.sub("", text)
    text = text.replace("\ufeff", "")
    text = _MULTI_SPACE.sub(" ", text)
    return text.strip()


def strip_combining(value: str, keep: set[str] | None = None) -> str:
    keep = keep or set()
    out = []
    for ch in unicodedata.normalize("NFD", value):
        if unicodedata.combining(ch) and ch not in keep:
            continue
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))


def detect_script(value: str) -> str:
    counts: dict[str, int] = {}
    for ch in value:
        if ch.isalpha():
            try:
                name = unicodedata.name(ch)
            except ValueError:
                continue
            if "ARABIC" in name or "FARSI" in name:
                counts["Arab"] = counts.get("Arab", 0) + 1
            elif "HEBREW" in name:
                counts["Hebr"] = counts.get("Hebr", 0) + 1
            elif "CYRILLIC" in name:
                counts["Cyrl"] = counts.get("Cyrl", 0) + 1
            elif "LATIN" in name:
                counts["Latn"] = counts.get("Latn", 0) + 1
            elif "ARMENIAN" in name:
                counts["Armn"] = counts.get("Armn", 0) + 1
    if not counts:
        return "Zyyy"
    return max(counts, key=counts.get)


def detect_language(value: str, hint: str | None = None) -> str:
    if hint:
        return hint
    script = detect_script(value)
    # Heuristic only — UI locale / dataset language override this.
    if script == "Arab":
        # Persian-specific letters
        if any(ch in value for ch in "پچژگکی"):
            return "fa"
        if any(ch in value for ch in "ێۆڕڵ"):
            return "ku"
        return "ar"
    if script == "Hebr":
        return "he"
    if script == "Cyrl":
        return "ru"
    return "en"
