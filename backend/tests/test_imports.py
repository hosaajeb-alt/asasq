import json
from pathlib import Path

from app.application.parsers import iter_rows, sniff_kind


def test_sniff():
    assert sniff_kind("a.csv") == "csv"
    assert sniff_kind("a.jsonl") == "jsonl"
    assert sniff_kind("a.parquet") == "parquet"


def test_csv_stream(tmp_path: Path):
    p = tmp_path / "t.csv"
    p.write_text("name,email\nAli,a@x.com\nSara,s@x.com\n", encoding="utf-8")
    rows = list(iter_rows(p, "t.csv"))
    assert len(rows) == 2
    assert rows[0]["email"] == "a@x.com"


def test_jsonl_stream(tmp_path: Path):
    p = tmp_path / "t.jsonl"
    p.write_text('{"name":"Ali"}\n{"name":"Sara"}\n', encoding="utf-8")
    rows = list(iter_rows(p, "t.jsonl"))
    assert [r["name"] for r in rows] == ["Ali", "Sara"]


def test_json_array(tmp_path: Path):
    p = tmp_path / "t.json"
    p.write_text(json.dumps({"records": [{"x": 1}, {"x": 2}]}), encoding="utf-8")
    rows = list(iter_rows(p, "t.json"))
    assert len(rows) == 2
