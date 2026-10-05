from app.normalization.engine import NormalizationEngine
from app.normalization.persian import normalize_persian
from app.normalization.turkish import casefold_turkish
from app.normalization.hebrew import normalize_hebrew
from app.normalization.arabic import normalize_arabic


def test_persian_yeh_kaf_and_diacritics():
    n = normalize_persian("محمّد رضایی")
    assert "ّ" not in n
    assert n == normalize_persian("محمد رضایی")
    assert normalize_persian("يك") == normalize_persian("یک")
    assert "ي" not in normalize_persian("علي")
    assert "ك" not in normalize_persian("كریم")


def test_tatweel_and_zwnj_stripped_for_matching():
    assert normalize_persian("مـحـمـد") == normalize_persian("محمد")
    assert "\u200c" not in normalize_persian("می\u200cخواهم")


def test_arabic_uses_arabic_yeh_not_persian():
    out = normalize_arabic("یکی")
    assert "ی" not in out  # folded to Arabic yeh


def test_turkish_dotted_i():
    assert casefold_turkish("İSTANBUL") == "istanbul"
    assert casefold_turkish("IĞDIR") == "ığdır"
    assert casefold_turkish("I") != casefold_turkish("İ") or True
    # I (dotless) → ı, İ (dotted) → i
    assert casefold_turkish("I") == "ı"
    assert casefold_turkish("İ") == "i"


def test_hebrew_final_forms():
    assert normalize_hebrew("שלום")  # smoke
    assert normalize_hebrew("לך") == normalize_hebrew("לכ")


def test_original_never_replaced():
    eng = NormalizationEngine()
    env = eng.normalize("محمّد رضایی", "PersonName", "fa")
    assert env.original_value == "محمّد رضایی"
    assert env.normalized_value != ""
    assert "Mohammad" in env.transliterated_value or "Muhammad" in env.transliterated_value
    assert env.phonetic_value != ""


def test_email_canonical():
    eng = NormalizationEngine()
    env = eng.normalize("  M.Rezaei@Example.COM ", "Email")
    assert env.canonical_value == "m.rezaei@example.com"
    assert env.is_valid
    bad = eng.normalize("not-an-email", "Email")
    assert bad.is_valid is False


def test_phone_digits():
    eng = NormalizationEngine()
    env = eng.normalize("+98 21 4455 0190", "Phone")
    assert env.canonical_value == "982144550190"
    assert env.original_value == "+98 21 4455 0190"
