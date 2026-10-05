# Implementation Roadmap

## Phase 1 — Foundation  ← this deliverable

Next.js + i18n EN/FA + RTL/LTR · FastAPI · PostgreSQL · Auth · Users/teams · Dataset metadata · Import wizard · Docker dev env · Architecture docs.

Also included so the product is usable, not an empty shell:

- Semantic type registry + schema detection + profiling + language-aware normalization
- In-app search with ranking presets
- Entity profiles, proposed matches, relationship graph canvas
- Investigations / evidence / audit log / data quality views
- Seeded demo data (synthetic, lawful)

## Phase 2 — Data intelligence (deepening)

Richer DQ, custom semantic types UI, duplicate levels at import scale, more language modules.

## Phase 3 — Search

OpenSearch cluster, multilingual analyzers, index-per-dataset-version, query expansion at the engine, ranking telemetry.

## Phase 4 — Entity intelligence

Distributed blocking, configurable rule DSL, graph database, merge/split workflows at volume.

## Phase 5 — Investigation

Report export, timeline playback, saved-search alerting, evidence packs.

## Phase 6 — Scale

Kafka ingest, ClickHouse analytics, object-store parquet layout, partitioning, horizontal workers, benchmarking against multi-billion synthetic sets.

## Non-goals (all phases)

Unauthorized collection, credential stuffing, exploit tooling, scraping of private data, anything designed to abuse leaked personal data.
