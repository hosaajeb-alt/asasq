from app.schema_detection.detector import SchemaDetector


def test_email_column_high_confidence():
    det = SchemaDetector()
    r = det.detect_column("mail", ["a@x.com", "b@y.org", "c@z.net", ""])
    assert r["semantic_type"] == "Email"
    assert r["confidence"] > 0.8
    assert r["approved"] is False


def test_phone_column():
    det = SchemaDetector()
    r = det.detect_column("phone_number", ["+1 202 555 0147", "+98 21 4455 0190", "202-555-0100"])
    assert r["semantic_type"] == "Phone"
    assert r["confidence"] > 0.8


def test_does_not_silently_approve():
    det = SchemaDetector()
    table = det.detect_table({"name": ["Ali", "Sara"], "notes": ["hello", "world"]})
    assert all(c["approved"] is False for c in table)


def test_free_text_fallback():
    det = SchemaDetector()
    r = det.detect_column("comments", ["lorem ipsum", "dolor sit"])
    assert r["semantic_type"] in ("FreeText", "PersonName")
    assert r["confidence"] < 0.9
