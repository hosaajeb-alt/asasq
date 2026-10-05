from __future__ import annotations

from app.normalization.arabic import normalize_arabic
from app.normalization.english import canonical_english_name, normalize_english
from app.normalization.envelope import ValueEnvelope
from app.normalization.hebrew import normalize_hebrew
from app.normalization.kurdish import normalize_kurdish
from app.normalization.persian import normalize_persian
from app.normalization.phonetic import phonetic_key
from app.normalization.russian import normalize_russian
from app.normalization.semantic import (
    canonical_domain,
    canonical_email,
    canonical_hash,
    canonical_ipv4,
    canonical_phone,
    canonical_url,
    canonical_username,
)
from app.normalization.transliteration import name_transliterations, scientific_transliterate
from app.normalization.turkish import normalize_turkish
from app.normalization.unicode_hygiene import detect_language, detect_script, hygiene

ValueEnvelope = ValueEnvelope  # re-export


_LANG_MODULES = {
    "fa": normalize_persian,
    "ar": normalize_arabic,
    "tr": normalize_turkish,
    "ku": normalize_kurdish,
    "he": normalize_hebrew,
    "ru": normalize_russian,
    "en": normalize_english,
}


class NormalizationEngine:
    """Dispatch by semantic type + language. Original is never overwritten."""

    def normalize(
        self,
        value: str | None,
        semantic_type: str = "FreeText",
        language: str | None = None,
    ) -> ValueEnvelope:
        original = "" if value is None else str(value)
        cleaned = hygiene(original)
        lang = detect_language(cleaned, language)
        script = detect_script(cleaned)
        notes: list[str] = []

        module = _LANG_MODULES.get(lang, normalize_english)
        matching = module(cleaned) if cleaned else ""
        translit = ""
        phonetic = ""
        canonical = matching
        valid = True

        st = semantic_type or "FreeText"

        if st == "Email":
            canonical, valid = canonical_email(cleaned)
            matching = canonical
        elif st == "Phone":
            canonical, valid = canonical_phone(cleaned)
            matching = canonical
        elif st == "Domain":
            canonical, valid = canonical_domain(cleaned)
            matching = canonical
        elif st == "URL":
            canonical, valid = canonical_url(cleaned)
            matching = canonical
        elif st in ("IPv4",):
            canonical, valid = canonical_ipv4(cleaned)
            matching = canonical
        elif st == "Username":
            canonical, valid = canonical_username(cleaned)
            matching = canonical
        elif st == "Hash":
            canonical, valid = canonical_hash(cleaned)
            matching = canonical
        elif st in ("PersonName", "OrganizationName"):
            if script == "Arab" or lang in ("fa", "ar", "ku"):
                forms = name_transliterations(matching or cleaned)
                translit = " | ".join(forms[:6])
            elif script == "Latn":
                translit = matching
                canonical = canonical_english_name(cleaned)
            else:
                translit = scientific_transliterate(matching or cleaned)
            phonetic = phonetic_key(matching or cleaned, script)
            notes.append("phonetic is a ranking signal, not identity")
        else:
            if script == "Arab":
                translit = scientific_transliterate(matching or cleaned)

        return ValueEnvelope(
            original_value=original,
            normalized_value=matching,
            canonical_value=canonical,
            transliterated_value=translit,
            phonetic_value=phonetic,
            language=lang,
            script=script,
            is_valid=valid if cleaned else True,
            notes=notes,
        )

    def block_keys(self, envelope: ValueEnvelope, semantic_type: str) -> list[str]:
        keys = []
        if envelope.canonical_value:
            keys.append(f"{semantic_type}:canon:{envelope.canonical_value.lower()}")
        if envelope.normalized_value:
            keys.append(f"{semantic_type}:norm:{envelope.normalized_value.lower()}")
        if envelope.phonetic_value:
            keys.append(f"{semantic_type}:ph:{envelope.phonetic_value}")
        if semantic_type in ("Email", "Phone", "Username", "Domain", "Hash", "Identifier"):
            # identifier blocks are strong
            if envelope.canonical_value:
                keys.append(f"id:{semantic_type}:{envelope.canonical_value.lower()}")
        # prefix block for names
        if semantic_type in ("PersonName", "OrganizationName") and envelope.normalized_value:
            token = envelope.normalized_value.split()[0][:4]
            keys.append(f"namepfx:{token}")
        return keys
