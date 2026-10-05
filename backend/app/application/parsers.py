"""Streaming parsers — never load a multi-GB file fully into RAM as a single object."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, Iterable, Iterator


def sniff_kind(filename: str, content_type: str = "") -> str:
    name = (filename or "").lower()
    if name.endswith(".csv") or "csv" in content_type:
        return "csv"
    if name.endswith(".jsonl") or name.endswith(".ndjson"):
        return "jsonl"
    if name.endswith(".parquet"):
        return "parquet"
    if name.endswith(".json"):
        return "json"
    return "csv"


def iter_rows(path: str | Path, filename: str, content_type: str = "", max_rows: int | None = None) -> Iterator[dict[str, Any]]:
    kind = sniff_kind(filename, content_type)
    path = Path(path)
    n = 0
    if kind == "csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(f, dialect=dialect)
            for row in reader:
                yield {k: (v if v is not None else "") for k, v in row.items()}
                n += 1
                if max_rows and n >= max_rows:
                    return
    elif kind == "jsonl":
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if isinstance(obj, dict):
                    yield obj
                    n += 1
                    if max_rows and n >= max_rows:
                        return
    elif kind == "json":
        # Stream-friendly for arrays: incremental load of the top-level array still
        # materializes it. For Phase 1 we parse then iterate; large JSON arrays
        # should be converted to JSONL. We still avoid keeping *processed* rows.
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        rows: Iterable[Any]
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            for key in ("records", "data", "rows", "items"):
                if isinstance(data.get(key), list):
                    rows = data[key]
                    break
            else:
                rows = [data]
        else:
            rows = []
        for obj in rows:
            if isinstance(obj, dict):
                yield obj
                n += 1
                if max_rows and n >= max_rows:
                    return
    elif kind == "parquet":
        import pyarrow.parquet as pq

        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches(batch_size=1024):
            for rec in batch.to_pylist():
                yield rec
                n += 1
                if max_rows and n >= max_rows:
                    return
    else:
        raise ValueError(f"unsupported format: {filename}")


def sample_columns(path: str | Path, filename: str, content_type: str = "", limit: int = 200) -> tuple[list[str], list[dict[str, Any]]]:
    rows = list(iter_rows(path, filename, content_type, max_rows=limit))
    cols: list[str] = []
    seen = set()
    for row in rows:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                cols.append(k)
    return cols, rows
