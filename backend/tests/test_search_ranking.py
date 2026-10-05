from app.search.ranking import MatchSignals, RANKING_PRESETS, rank_score


def test_exact_outranks_phonetic_in_high_precision():
    exact = MatchSignals(exact=1.0, source=1.0)
    phonetic = MatchSignals(phonetic=1.0, source=1.0)
    s1, w1 = rank_score(exact, "high_precision")
    s2, w2 = rank_score(phonetic, "high_precision")
    assert s1 > s2
    assert "exact match" in w1


def test_presets_exist():
    for k in ("exact", "high_precision", "balanced", "broad"):
        assert k in RANKING_PRESETS
        assert "phonetic" in RANKING_PRESETS[k]


def test_broad_gives_phonetic_more_weight():
    sig = MatchSignals(phonetic=1.0, source=1.0)
    broad, _ = rank_score(sig, "broad")
    exact_mode, _ = rank_score(sig, "exact")
    assert broad > exact_mode
