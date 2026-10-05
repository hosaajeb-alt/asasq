from __future__ import annotations

from collections import Counter
from typing import Any

from app.normalization.engine import NormalizationEngine
from app.normalization.unicode_hygiene import detect_language, detect_script
from app.schema_detection.detector import SchemaDetector


class DataProfiler:
    def __init__(self) -> None:
        self.engine = NormalizationEngine()
        self.detector = SchemaDetector()

    def profile(
        self,
        rows: list[dict[str, Any]],
        schema: list[dict[str, Any]] | None = None,
        dataset_name: str = "",
    ) -> dict[str, Any]:
        n = len(rows)
        if schema is None:
            cols: dict[str, list[Any]] = {}
            for row in rows:
                for k, v in row.items():
                    cols.setdefault(k, []).append(v)
            schema = self.detector.detect_table(cols)

        hashes: Counter[str] = Counter()
        invalid_by_field: dict[str, int] = {f["name"]: 0 for f in schema}
        field_stats: list[dict[str, Any]] = []

        for field in schema:
            name = field["name"]
            st = field.get("semantic_type") or "FreeText"
            values = [row.get(name) for row in rows]
            nonempty = [v for v in values if v not in (None, "")]
            originals = [str(v) for v in nonempty]
            envelopes = [self.engine.normalize(v, st) for v in originals]
            invalid = sum(1 for e in envelopes if not e.is_valid)
            invalid_by_field[name] = invalid
            unique = len({e.canonical_value or e.normalized_value for e in envelopes})
            langs = Counter(detect_language(v) for v in originals[:500])
            scripts = Counter(detect_script(v) for v in originals[:500])
            card = unique
            field_stats.append(
                {
                    "field": name,
                    "physical_type": field.get("physical_type"),
                    "semantic_type": st,
                    "null_rate": round((n - len(nonempty)) / max(n, 1), 4),
                    "unique_rate": round(unique / max(len(nonempty), 1), 4),
                    "duplicate_rate": round(1 - (unique / max(len(nonempty), 1)), 4) if nonempty else 0,
                    "invalid_rate": round(invalid / max(n, 1), 4),
                    "cardinality": card,
                    "language_distribution": dict(langs),
                    "script_distribution": dict(scripts),
                    "sample_values": originals[:8],
                }
            )

        for row in rows:
            key = "|".join(str(row.get(f["name"], "")) for f in schema)
            hashes[key] += 1
        duplicate_rows = sum(c - 1 for c in hashes.values() if c > 1)

        missing_email = 0
        invalid_phone = 0
        for f in schema:
            if f.get("semantic_type") == "Email":
                missing_email = sum(1 for row in rows if not row.get(f["name"]))
            if f.get("semantic_type") == "Phone":
                invalid_phone = invalid_by_field.get(f["name"], 0)

        valid = n - duplicate_rows  # loose: non-dup rows; invalids reported separately
        return {
            "dataset": dataset_name,
            "records": n,
            "valid": max(n - sum(1 for row in rows if all(v in (None, "") for v in row.values())), 0),
            "duplicates": duplicate_rows,
            "missing_email": missing_email,
            "invalid_phone": invalid_phone,
            "fields": field_stats,
            "valid_non_empty": valid,
        }
