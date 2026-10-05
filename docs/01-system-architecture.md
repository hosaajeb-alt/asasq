# NEXUS System Architecture

**NEXUS** is a lawful OSINT / data-intelligence platform. It sits between a large-scale search engine, a data-management system, an entity-resolution engine, an investigation workspace, and a graph intelligence layer.

This document records the architectural decisions for a system that must eventually hold **10+ billion records** without treating PostgreSQL as the system of record for raw facts.

---

## 1. Design principles

1. **Original data is immutable.** Imports write once to the raw layer. Normalization never overwrites the source.
2. **Normalized data is derived.** It can be recomputed from the raw layer plus a versioned rule set.
3. **Search indexes are not the source of truth.** They are projections. Rebuild them from raw + entity layers.
4. **Entity resolution is probabilistic and explainable.** Similarity is not identity. Auto-merge is opt-in and rule-gated.
5. **Every important attribute has provenance.** Analysts can always answer *where did this come from?* and *when was it added?*
6. **Inference is visually distinct from observation.** Observed / derived / inferred / user-confirmed are first-class statuses.
7. **Multilingual by design.** English + Persian (RTL/LTR) in Phase 1; language-aware normalization, not a single Unicode hammer.
8. **Horizontal scale.** Every hot path is shardable. Phase 1 uses PostgreSQL for metadata and a bounded record store; later phases swap storage backends behind the same ports.
9. **Lawful use only.** No collection tooling, no credential theft, no exploitation. Datasets are imported by authorized operators.

---

## 2. Logical layers

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web UI  (Next.js)                       │
│          i18n EN/FA · RTL/LTR · investigation workspace         │
└───────────────────────────────┬─────────────────────────────────┘
                                │  HTTPS / JSON
┌───────────────────────────────▼─────────────────────────────────┐
│                    Investigation API  (FastAPI)                 │
│     auth · RBAC · validation · audit · job orchestration        │
└───────┬──────────┬──────────┬──────────┬──────────┬─────────────┘
        │          │          │          │          │
        ▼          ▼          ▼          ▼          ▼
   Metadata    Raw/Object  Analytics   Search     Graph
   PostgreSQL  MinIO/S3    ClickHouse  OpenSearch Neo4j
        │          │          │          │          │
        └──────────┴────┬─────┴──────────┴──────────┘
                        ▼
                 Processing workers
            (normalization, profiling, ER, index)
                        ▲
                        │
                   Queue (Kafka / Redis)
```

### Layer contracts

| Layer | Authority | Typical store | Phase 1 stand-in |
|---|---|---|---|
| **Raw** | Source of truth for imported bytes and parsed rows | S3/MinIO (Parquet/JSONL) + object manifest in PG | Local volume + PG `records.raw_payload` |
| **Normalized** | Derived representations of each value | Columnar (Parquet / ClickHouse) | PG `record_values` |
| **Entity** | Canonical real-world objects + links | Graph DB + PG metadata | PG `entities`, `relationships` |
| **Search** | Query projection | OpenSearch | PG FTS + trigram + in-app ranker |
| **Analytics** | Aggregations, DQ, cardinality | ClickHouse | PG materialized views / SQL |
| **Application** | Users, ACL, cases, audit, schema registry | PostgreSQL | PostgreSQL |

Storage backends are selected through ports in `app/infrastructure`. Swapping PostgreSQL FTS for OpenSearch does not change API or UI.

---

## 3. Ingestion pipeline (target)

```
Authorized file
      │
      ▼
  Upload API  ──►  Object store (raw, immutable)
      │
      ▼
  Import job (queued → processing → completed | failed | paused | cancelled)
      │
      ├─► Schema detection (proposal, human-approved)
      ├─► Field mapping against Semantic Field Registry
      ├─► Language-aware normalization (original preserved)
      ├─► Data quality profile (human review before commit)
      ├─► Streamed parse (never whole-file in RAM)
      ├─► Partitioned write: raw parquet + normalized + search docs
      └─► Blocking keys for later entity resolution
```

Large files are read as streams/chunks. Progress is `records_processed`, `records_per_sec`, ETA, errors, invalid counts.

---

## 4. Runtime topology (target vs Phase 1)

### Target (Phase 6)

- **Edge / UI:** Next.js, statically + SSR where useful, locale-aware.
- **API:** FastAPI, horizontally replicated, stateless, JWT + session denylist in Redis.
- **Workers:** Kafka consumers for ingest, ER, index, DQ.
- **Metadata PG:** primary + replica. Partition audit_logs by month.
- **ClickHouse:** records, profiles, quality metrics. Partition by dataset_id + month.
- **OpenSearch:** search documents, sharded by dataset hash, ILM.
- **Neo4j / Memgraph:** entity graph, relationships with evidence ids.
- **MinIO/S3:** raw files, parquet, export artifacts, report PDFs.
- **Redis:** cache, rate limit, job leases, search session.
- **Observability:** OpenTelemetry → Prometheus / Grafana / Loki / Tempo.

### Phase 1 (this deliverable)

- Next.js UI + FastAPI + PostgreSQL + Redis + local object volume.
- In-process / Redis-backed job runner (interface ready for Kafka).
- Search via PostgreSQL (`pg_trgm`, FTS) plus application ranking.
- Graph via PostgreSQL adjacency + UI canvas.
- Same domain model and API shapes as the target.

---

## 5. Consistency model

- **Raw objects:** write-once, checksummed (SHA-256).
- **Metadata (datasets, schema, ACL, cases):** strong consistency in PostgreSQL.
- **Search / analytics / graph projections:** eventually consistent. Each projection stores `source_revision`.
- **Entity merges:** transactional in the entity store; projections updated asynchronously; merges are reversible (`entity_unmerge` audit event).

---

## 6. Multi-tenancy and isolation

Phase 1 is **RBAC on a shared cluster**: users, teams, roles, dataset grants, case grants.

Designed for later **ABAC**: every authorization check goes through `AccessPolicy.evaluate(principal, action, resource, context)` so attributes (clearance, legal classification, geo, purpose) can be added without rewriting callers.

Row-level: datasets and cases carry `classification` and ACL. Search always filters by visible dataset ids **before** ranking.

---

## 7. Failure and durability

- Import jobs are idempotent on `(dataset_id, version, content_checksum)`.
- Workers heartbeat; stalled jobs are re-queued.
- Search rebuild is a projection replay, not a restore.
- Audit log is append-only at the application layer (no UPDATE/DELETE in repositories).

---

## 8. Security baseline

- Passwords hashed with bcrypt (cost ≥ 12).
- JWT access + refresh; refresh rotation.
- CORS locked to the UI origin in production.
- Rate limiting on auth and export.
- Server-side authorization on every route (never UI-only).
- Uploads: size limits, MIME allowlist, streaming, no path-controlled filenames.
- Secrets from environment / future vault; never in images.
- Structured logs redact emails, phones, national ids.

---

## 9. Bounded contexts (code layout)

```
domain/                 # entities, value objects, invariants
application/            # use-cases, DTOs, ports
infrastructure/         # SQL, object store, search, queue adapters
api/                    # FastAPI routers, deps
normalization/          # language-aware modules
entity_resolution/      # blocking, scoring, explain
search/                 # query expansion, ranking
workers/                # job handlers
```

The UI never talks to storage engines directly.

---

## 10. What Phase 1 deliberately does not run

Kafka, ClickHouse, OpenSearch, Neo4j. Docker Compose includes commented / optional profiles so they can be attached without rewriting the application ports.
