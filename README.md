# NEXUS Intelligence Platform

Lawful OSINT / data-intelligence workspace: dataset management, multilingual search, entity resolution, graph analysis, and investigation cases.

NEXUS is designed for **authorized** datasets only. Original values are immutable. Search indexes are projections, not the source of truth. Entity resolution is probabilistic and explainable — similarity is not identity.

Languages: **English (LTR)** and **Persian (RTL)**, switchable without reload.

## Architecture (target)

```
Import → Queue → Workers
              ├─ Object store (raw / parquet)
              ├─ ClickHouse (analytics)
              ├─ OpenSearch (search)
              └─ Entity / graph layer
                    → Investigation API → Next.js UI
```

PostgreSQL holds **application metadata** (users, ACL, dataset catalog, cases, audit). It is not the 10B-record store.

Phase 1 (this repo) runs the same domain model on PostgreSQL + a local object volume, with Redis and MinIO in Compose so later engines can attach without rewriting ports.

Documents:

- [System architecture](docs/01-system-architecture.md)
- [Database schema](docs/02-database-schema.md)
- [Entity model](docs/03-entity-model.md)
- [Dataset model](docs/04-dataset-model.md)
- [Search document schema](docs/05-search-document-schema.md)
- [Semantic type registry](docs/06-semantic-type-registry.md)
- [Normalization](docs/07-normalization-architecture.md)
- [Entity resolution](docs/08-entity-resolution-architecture.md)
- [API](docs/09-api-specification.md)
- [Frontend IA](docs/10-frontend-ia.md)
- [Roadmap](docs/11-implementation-roadmap.md)
- [Docker](docs/12-docker-dev-environment.md)

## Run

```bash
cp .env.example .env
docker compose up --build
```

- UI: http://localhost:3000
- API: http://localhost:8000/api/docs

Without Docker (SQLite stand-in for metadata — not the 10B path):

```bash
# API
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
USE_SQLITE=true SQLITE_PATH=../data/nexus.db DATA_DIR=../data \
  .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# UI
cd frontend && npm install
INTERNAL_API_URL=http://127.0.0.1:8000 npm run dev -- -H 0.0.0.0 -p 3000
```

Demo logins (change before any shared deploy):

| User | Password | Role |
|---|---|---|
| `admin@nexus.local` | `NexusAdmin!23` | admin |
| `analyst@nexus.local` | `NexusAnalyst!23` | analyst |
| `investigator@nexus.local` | `NexusInvest!23` | investigator |

Seed data is **synthetic** (fictional people and `.example` domains) so the workspace is populated for search, ER, graph, and cases.

A sample file for the import wizard: [`samples/researchers.csv`](samples/researchers.csv).

## Tests

```bash
cd backend && pytest -q
```

Coverage includes Persian/Turkish/Hebrew normalization, schema detection, blocking ER, ranking presets, RBAC, and streaming parsers.

## Product principles

1. Original data is immutable.
2. Normalized data is derived.
3. Search indexes are not the source of truth.
4. Entity resolution is probabilistic and explainable.
5. Every important attribute has provenance.
6. Similarity is not identity.
7. Inference is visually distinct from observation.
8. Multilingual by design.
9. Horizontal scale.
10. Lawful, authorized data use only.
