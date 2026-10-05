"""Transliteration strategies. Always stored separately from the original."""

from __future__ import annotations

_FA_AR = {
    "ا": "a",
    "آ": "a",
    "ب": "b",
    "پ": "p",
    "ت": "t",
    "ث": "s",
    "ج": "j",
    "چ": "ch",
    "ح": "h",
    "خ": "kh",
    "د": "d",
    "ذ": "z",
    "ر": "r",
    "ز": "z",
    "ژ": "zh",
    "س": "s",
    "ش": "sh",
    "ص": "s",
    "ض": "z",
    "ط": "t",
    "ظ": "z",
    "ع": "a",
    "غ": "gh",
    "ف": "f",
    "ق": "q",
    "ک": "k",
    "ك": "k",
    "گ": "g",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "و": "v",
    "ه": "h",
    "ی": "i",
    "ي": "i",
    "ى": "i",
    "ئ": "i",
    "ة": "h",
    " ": " ",
}

# Common given-name overrides (colloquial strategy).
_NAME_ALIASES = {
    "محمد": ["Mohammad", "Muhammad", "Mohamed", "Mohammed"],
    "محمّد": ["Mohammad", "Muhammad"],
    "علی": ["Ali"],
    "حسن": ["Hassan", "Hasan"],
    "حسین": ["Hossein", "Hussein", "Husayn"],
    "رضا": ["Reza", "Riza"],
    "رضایی": ["Rezaei", "Rezaee", "Rezaie"],
    "زهرا": ["Zahra"],
    "فاطمه": ["Fatemeh", "Fatima"],
    "سارا": ["Sara", "Sarah"],
    "مریم": ["Maryam", "Mariam"],
    "امیر": ["Amir", "Ameir"],
    "نرگس": ["Narges", "Nargess"],
    "احمدی": ["Ahmadi"],
    "کریمی": ["Karimi"],
    "موسوی": ["Mousavi", "Musawi"],
    "کاظمی": ["Kazemi"],
    "جعفری": ["Jafari", "Jaafari"],
    "محمدی": ["Mohammadi"],
    "نوری": ["Nouri", "Nuri"],
    "صالحی": ["Salehi"],
}


def scientific_transliterate(value: str) -> str:
    out = []
    for ch in value:
        out.append(_FA_AR.get(ch, ch if ch.isascii() else ""))
    text = "".join(out)
    text = " ".join(part.capitalize() if part.isalpha() else part for part in text.split())
    return text.strip()


def name_transliterations(value: str) -> list[str]:
    """Return multiple Latin forms; original is never replaced."""
    parts = value.split()
    if not parts:
        return []
    # If the whole token has a known alias list, explode combinations modestly.
    options_per_part: list[list[str]] = []
    for part in parts:
        aliases = _NAME_ALIASES.get(part)
        if aliases:
            options_per_part.append(aliases)
        else:
            sci = scientific_transliterate(part)
            options_per_part.append([sci] if sci else [part])
    # Cartesian product capped.
    combos = [""]
    for opts in options_per_part:
        nxt = []
        for prefix in combos:
            for o in opts:
                nxt.append((prefix + " " + o).strip())
                if len(nxt) > 16:
                    break
            if len(nxt) > 16:
                break
        combos = nxt
    # Always include scientific of the whole string.
    sci = scientific_transliterate(value)
    if sci and sci not in combos:
        combos.insert(0, sci)
    return [c for c in combos if c]
