from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable

from app.normalization.semantic import (
    DOMAIN_RE,
    EMAIL_RE,
    HASH_RE,
    IPV4_RE,
    PHONE_RE,
    URL_RE,
)
from app.normalization.unicode_hygiene import detect_language, detect_script

NAME_HINTS: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"^(e[-_]?mail|mail)$", re.I), "Email", 0.95),
    (re.compile(r"(email|mail_address)", re.I), "Email", 0.85),
    (re.compile(r"^(phone|tel|mobile|cell|msisdn)$", re.I), "Phone", 0.95),
    (re.compile(r"(phone|mobile|tel[_-]?(no|num))", re.I), "Phone", 0.85),
    (re.compile(r"^(user(name)?|login|handle)$", re.I), "Username", 0.9),
    (re.compile(r"(user[_-]?name|handle)", re.I), "Username", 0.75),
    (re.compile(r"^(url|website|homepage|href)$", re.I), "URL", 0.92),
    (re.compile(r"^(domain|host|fqdn)$", re.I), "Domain", 0.92),
    (re.compile(r"^(ipv4|ip[_-]?address|ip)$", re.I), "IPv4", 0.9),
    (re.compile(r"^ipv6$", re.I), "IPv6", 0.95),
    (re.compile(r"^(full[_-]?name|display[_-]?name|person[_-]?name|name)$", re.I), "PersonName", 0.8),
    (re.compile(r"(first|given|last|family|sur)[_-]?name", re.I), "PersonName", 0.88),
    (re.compile(r"^(org|organization|company|employer|biz)$", re.I), "OrganizationName", 0.9),
    (re.compile(r"(company|organization|org[_-]?name)", re.I), "OrganizationName", 0.8),
    (re.compile(r"^city$", re.I), "City", 0.92),
    (re.compile(r"^country$", re.I), "Country", 0.92),
    (re.compile(r"(address|street|addr)", re.I), "Address", 0.8),
    (re.compile(r"(lat|lon|lng|coord)", re.I), "Coordinates", 0.75),
    (re.compile(r"(created|updated|timestamp|datetime|time)", re.I), "Timestamp", 0.7),
    (re.compile(r"^(date|dob|birth)", re.I), "Date", 0.75),
    (re.compile(r"(md5|sha1|sha256|hash|checksum)", re.I), "Hash", 0.9),
    (re.compile(r"(doc[_-]?id|document[_-]?id|passport|national[_-]?id)", re.I), "DocumentID", 0.8),
    (re.compile(r"(id)$", re.I), "Identifier", 0.45),
    (re.compile(r"(amount|price|usd|eur|currency)", re.I), "Currency", 0.7),
]

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
INT_RE = re.compile(r"^-?\d+$")
FLOAT_RE = re.compile(r"^-?\d+\.\d+$")
BOOL_RE = re.compile(r"^(true|false|yes|no|0|1)$", re.I)


def _value_vote(sample: str) -> str | None:
    s = sample.strip()
    if not s:
        return None
    if EMAIL_RE.match(s):
        return "Email"
    if URL_RE.match(s):
        return "URL"
    if IPV4_RE.match(s) and all(0 <= int(p) <= 255 for p in s.split(".") if p.isdigit()):
        return "IPv4"
    if HASH_RE.match(s):
        return "Hash"
    if PHONE_RE.match(s) and len(re.sub(r"\D", "", s)) >= 8:
        return "Phone"
    if DOMAIN_RE.match(s) and " " not in s:
        return "Domain"
    if DATE_RE.match(s):
        return "Date"
    return None


def _physical(sample_values: list[str]) -> str:
    nonempty = [v for v in sample_values if v and str(v).strip()]
    if not nonempty:
        return "string"
    n = len(nonempty)
    if sum(1 for v in nonempty if INT_RE.match(str(v))) / n > 0.9:
        return "integer"
    if sum(1 for v in nonempty if FLOAT_RE.match(str(v)) or INT_RE.match(str(v))) / n > 0.9:
        return "float"
    if sum(1 for v in nonempty if BOOL_RE.match(str(v))) / n > 0.9:
        return "boolean"
    if sum(1 for v in nonempty if DATE_RE.match(str(v))) / n > 0.8:
        return "date"
    return "string"


class SchemaDetector:
    """Propose semantic mappings. Never writes. Operator must approve."""

    def detect_column(self, name: str, values: Iterable[Any]) -> dict[str, Any]:
        samples = ["" if v is None else str(v) for v in values]
        nonempty = [v for v in samples if v.strip()]
        physical = _physical(samples)

        hint_type, hint_score = None, 0.0
        for rx, st, score in NAME_HINTS:
            if rx.search(name or ""):
                hint_type, hint_score = st, score
                break

        votes: Counter[str] = Counter()
        for v in nonempty[:500]:
            st = _value_vote(v)
            if st:
                votes[st] += 1

        value_type, value_score = None, 0.0
        if nonempty and votes:
            value_type, n = votes.most_common(1)[0]
            value_score = n / max(len(nonempty[:500]), 1)

        if hint_type and value_type and hint_type == value_type:
            semantic = hint_type
            confidence = min(0.99, 0.55 * hint_score + 0.45 * value_score + 0.15)
        elif hint_type and (not value_type or value_score < 0.3):
            semantic = hint_type
            confidence = hint_score * 0.85
        elif value_type:
            semantic = value_type
            confidence = 0.5 + 0.45 * value_score
        else:
            semantic = "PersonName" if (name or "").lower() in {"name", "full_name"} else "FreeText"
            confidence = 0.35 if semantic == "PersonName" else 0.25

        langs = Counter(detect_language(v) for v in nonempty[:200])
        scripts = Counter(detect_script(v) for v in nonempty[:200])

        return {
            "name": name,
            "physical_type": physical,
            "semantic_type": semantic,
            "confidence": round(float(confidence), 3),
            "hint": hint_type,
            "value_vote": value_type,
            "null_rate": round(1 - (len(nonempty) / max(len(samples), 1)), 4),
            "language_distribution": dict(langs),
            "script_distribution": dict(scripts),
            "sample_values": nonempty[:8],
            "approved": False,
        }

    def detect_table(self, columns: dict[str, list[Any]]) -> list[dict[str, Any]]:
        return [self.detect_column(name, vals) for name, vals in columns.items()]
