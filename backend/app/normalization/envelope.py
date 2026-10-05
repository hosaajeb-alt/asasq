from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValueEnvelope:
    original_value: str
    normalized_value: str
    canonical_value: str
    transliterated_value: str = ""
    phonetic_value: str = ""
    language: str = ""
    script: str = ""
    is_valid: bool = True
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "original_value": self.original_value,
            "normalized_value": self.normalized_value,
            "canonical_value": self.canonical_value,
            "transliterated_value": self.transliterated_value,
            "phonetic_value": self.phonetic_value,
            "language": self.language,
            "script": self.script,
            "is_valid": self.is_valid,
            "notes": self.notes,
        }
