from app.entity_resolution.blocking import generate_candidates
from app.entity_resolution.engine import EntityResolutionEngine
from app.entity_resolution.scoring import score_pair


def _rec(i, **attrs):
    keys = []
    for st, env in attrs.items():
        if env.get("canonical_value"):
            keys.append(f"id:{st}:{env['canonical_value'].lower()}")
            keys.append(f"{st}:canon:{env['canonical_value'].lower()}")
    return {"id": str(i), "block_keys": keys, "attributes": attrs}


def test_name_only_never_autolink():
    a = {"PersonName": {"canonical_value": "محمد رضایی", "normalized_value": "محمد رضایی"}}
    b = {"PersonName": {"canonical_value": "محمد رضایی", "normalized_value": "محمد رضایی"}}
    expl = score_pair(a, b)
    assert expl.auto_link_eligible is False
    assert expl.confidence > 0.2


def test_same_email_and_similar_name_is_strong():
    a = {
        "PersonName": {
            "canonical_value": "محمد رضایی",
            "normalized_value": "محمد رضایی",
            "transliterated_value": "Mohammad Rezaei",
            "phonetic_value": "MHMD",
        },
        "Email": {"canonical_value": "m.rezaei@example.com"},
        "City": {"canonical_value": "tehran"},
    }
    b = {
        "PersonName": {
            "canonical_value": "mohammad rezaee",
            "normalized_value": "Mohammad Rezaee",
            "transliterated_value": "Mohammad Rezaee",
            "phonetic_value": "MHMTR",
        },
        "Email": {"canonical_value": "m.rezaei@example.com"},
        "City": {"canonical_value": "tehran"},
    }
    expl = score_pair(a, b)
    assert expl.confidence >= 0.7
    assert "same normalized email" in expl.reasons
    assert expl.auto_link_eligible is True


def test_blocking_not_quadratic():
    records = [
        _rec(1, Email={"canonical_value": "a@x.com"}),
        _rec(2, Email={"canonical_value": "a@x.com"}),
        _rec(3, Email={"canonical_value": "b@x.com"}),
        _rec(4, Email={"canonical_value": "c@x.com"}),
    ]
    pairs = generate_candidates(records)
    ids = {(a, b) for a, b, _ in pairs}
    assert ("1", "2") in ids
    assert ("3", "4") not in ids
    assert len(pairs) == 1


def test_engine_proposes_sorted():
    records = [
        _rec(
            1,
            Email={"canonical_value": "m@x.com"},
            PersonName={"canonical_value": "ali", "normalized_value": "ali"},
        ),
        _rec(
            2,
            Email={"canonical_value": "m@x.com"},
            PersonName={"canonical_value": "ali", "normalized_value": "ali"},
        ),
    ]
    out = EntityResolutionEngine().propose(records, min_confidence=0.4)
    assert out and out[0]["confidence"] >= 0.4
    assert out[0]["status"] == "proposed"
