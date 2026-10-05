"""Semantic-type specific canonicalization (email, phone, domain, …)."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
IPV6_RE = re.compile(r"^[0-9a-fA-F:]+$")
PHONE_RE = re.compile(r"^\+?[\d\s().\-]{7,20}$")
HASH_RE = re.compile(r"^[0-9a-fA-F]{32}$|^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$")
URL_RE = re.compile(r"^https?://", re.I)
DOMAIN_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$", re.I)


def canonical_email(value: str) -> tuple[str, bool]:
    v = value.strip()
    if not EMAIL_RE.match(v):
        return v.lower(), False
    local, _, domain = v.partition("@")
    return f"{local.lower()}@{domain.lower()}", True


def canonical_phone(value: str) -> tuple[str, bool]:
    digits = re.sub(r"\D", "", value)
    if len(digits) < 7 or len(digits) > 15:
        return digits, False
    return digits, True


def canonical_domain(value: str) -> tuple[str, bool]:
    v = value.strip().lower().rstrip(".")
    v = v.replace("http://", "").replace("https://", "").split("/")[0]
    ok = bool(DOMAIN_RE.match(v))
    return v, ok


def canonical_url(value: str) -> tuple[str, bool]:
    v = value.strip()
    if not URL_RE.match(v):
        if DOMAIN_RE.match(v):
            return f"http://{v.lower()}", True
        return v, False
    parts = urlsplit(v)
    host = (parts.hostname or "").lower()
    path = parts.path or ""
    return f"{parts.scheme}://{host}{path}", True


def canonical_ipv4(value: str) -> tuple[str, bool]:
    v = value.strip()
    if not IPV4_RE.match(v):
        return v, False
    try:
        ok = all(0 <= int(p) <= 255 for p in v.split("."))
    except ValueError:
        ok = False
    return v, ok


def canonical_username(value: str) -> tuple[str, bool]:
    v = value.strip()
    return v.lower(), bool(v)


def canonical_hash(value: str) -> tuple[str, bool]:
    v = value.strip().lower()
    return v, bool(HASH_RE.match(v))
