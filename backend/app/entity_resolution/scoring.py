from __future__ import annotations

from dataclasses import dataclass, field


def _jaro(s1: str, s2: str) -> float:
    if s1 == s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    match_dist = max(len(s1), len(s2)) // 2 - 1
    match_dist = max(match_dist, 0)
    s1_m = [False] * len(s1)
    s2_m = [False] * len(s2)
    matches = 0
    transpositions = 0
    for i, ch in enumerate(s1):
        start = max(0, i - match_dist)
        end = min(i + match_dist + 1, len(s2))
        for j in range(start, end):
            if s2_m[j]:
                continue
            if ch != s2[j]:
                continue
            s1_m[i] = s2_m[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0
    k = 0
    for i, ch in enumerate(s1):
        if not s1_m[i]:
            continue
        while not s2_m[k]:
            k += 1
        if ch != s2[k]:
            transpositions += 1
        k += 1
    m = matches
    jaro = (m / len(s1) + m / len(s2) + (m - transpositions / 2) / m) / 3.0
    # Winkler prefix bonus
    prefix = 0
    for a, b in zip(s1, s2):
        if a == b and prefix < 4:
            prefix += 1
        else:
            break
    return jaro + prefix * 0.1 * (1 - jaro)


def token_jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


@dataclass
class ScoreExplain:
    confidence: float
    reasons: list[str] = field(default_factory=list)
    components: dict[str, float] = field(default_factory=dict)
    auto_link_eligible: bool = False


def score_pair(a: dict, b: dict) -> ScoreExplain:
    """a/b are dicts of semantic_type -> envelope-like dicts.

    Name-only matches never auto-link.
    """
    reasons: list[str] = []
    components: dict[str, float] = {}
    score = 0.0
    strong_id = False

    def get(rec: dict, st: str) -> str:
        env = rec.get(st) or {}
        return (env.get("canonical_value") or env.get("normalized_value") or "").strip()

    email_a, email_b = get(a, "Email"), get(b, "Email")
    if email_a and email_b and email_a.lower() == email_b.lower():
        score += 0.45
        strong_id = True
        reasons.append("same normalized email")
        components["email"] = 0.45

    phone_a, phone_b = get(a, "Phone"), get(b, "Phone")
    if phone_a and phone_b and phone_a == phone_b:
        score += 0.40
        strong_id = True
        reasons.append("same normalized phone")
        components["phone"] = 0.40
    elif phone_a and phone_b:
        reasons.append("different phone")

    user_a, user_b = get(a, "Username"), get(b, "Username")
    if user_a and user_b and user_a.lower() == user_b.lower():
        score += 0.35
        strong_id = True
        reasons.append("same username")
        components["username"] = 0.35

    name_a = get(a, "PersonName") or get(a, "OrganizationName")
    name_b = get(b, "PersonName") or get(b, "OrganizationName")
    tr_a = (a.get("PersonName") or a.get("OrganizationName") or {}).get("transliterated_value", "")
    tr_b = (b.get("PersonName") or b.get("OrganizationName") or {}).get("transliterated_value", "")
    if name_a and name_b:
        forms_a = [name_a.lower(), *[x.strip().lower() for x in tr_a.split("|") if x.strip()]]
        forms_b = [name_b.lower(), *[x.strip().lower() for x in tr_b.split("|") if x.strip()]]
        sim = 0.0
        for x in forms_a:
            for y in forms_b:
                sim = max(sim, _jaro(x, y), token_jaccard(x, y))
        contrib = round(0.35 * sim, 3)
        score += contrib
        components["name"] = contrib
        if sim >= 0.92:
            reasons.append(f"similar normalized name ({sim:.2f})")
        elif sim >= 0.75:
            reasons.append(f"partially similar name ({sim:.2f})")
        else:
            reasons.append(f"weak name similarity ({sim:.2f})")

        if tr_a and tr_b:
            best = 0.0
            for x in tr_a.split("|"):
                for y in tr_b.split("|"):
                    best = max(best, _jaro(x.strip().lower(), y.strip().lower()))
            if best >= 0.9:
                score += 0.10
                components["transliteration"] = 0.10
                reasons.append("transliteration similarity")
        ph_a = (a.get("PersonName") or {}).get("phonetic_value", "")
        ph_b = (b.get("PersonName") or {}).get("phonetic_value", "")
        if ph_a and ph_b and ph_a == ph_b:
            score += 0.06
            components["phonetic"] = 0.06
            reasons.append("same phonetic key (ranking signal only)")

    city_a, city_b = get(a, "City"), get(b, "City")
    if city_a and city_b and city_a.lower() == city_b.lower():
        score += 0.05
        components["city"] = 0.05
        reasons.append("same city")

    confidence = max(0.0, min(1.0, score))
    auto = strong_id and confidence >= 0.85 and bool(name_a and name_b)
    # Name-only: never auto
    if not strong_id:
        auto = False
    return ScoreExplain(
        confidence=round(confidence, 4),
        reasons=reasons,
        components=components,
        auto_link_eligible=auto,
    )
