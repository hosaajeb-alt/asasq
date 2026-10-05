# Database Schema (PostgreSQL — application / metadata)

PostgreSQL is the **system of record for application state**, not for 10B raw facts. In later phases, `records` and `record_values` move to object storage + ClickHouse; the table shapes below remain the logical model.

All primary keys are UUID v4. Timestamps are `timestamptz`. Soft-delete is explicit (`deleted_at`) and unused for audit logs.

---

## ER overview

```
users ─┬─ team_members ─ teams
       ├─ audit_logs
       ├─ datasets ─┬─ dataset_versions ─ dataset_fields
       │            ├─ import_jobs
       │            ├─ records ─ record_values
       │            └─ dataset_acl
       ├─ entities ─┬─ entity_attributes
       │            ├─ entity_aliases
       │            ├─ entity_record_links
       │            └─ relationships
       ├─ investigations ─┬─ investigation_items
       │                  ├─ notes
       │                  ├─ evidence
       │                  └─ timeline_events
       ├─ tags / taggings
       └─ semantic_types  (field registry)
```

---

## Core tables

### users
| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| email | citext unique | login |
| hashed_password | text | bcrypt |
| display_name | text | |
| locale | text | `en` \| `fa` |
| is_active | bool | |
| role | text | `admin` `analyst` `investigator` `viewer` |
| last_login_at | timestamptz | |
| created_at / updated_at | timestamptz | |

### teams, team_members
Teams own datasets and cases. `team_members.role` is `owner` `editor` `viewer`.

### datasets
| Column | Type | Notes |
|---|---|---|
| id | uuid pk | |
| slug | text unique | stable key |
| name, description | text | searchable |
| category | text | registry, people, network, documents, custom |
| source, source_description | text | |
| dataset_date, imported_at | date / timestamptz | |
| languages | text[] | |
| geographic_scope | text | |
| version_label | text | current version, e.g. `v3` |
| legal_classification | text | `public` `internal` `confidential` `restricted` |
| tags | text[] | |
| notes | text | |
| record_count | bigint | |
| processing_status | text | `draft` `queued` `processing` `ready` `failed` |
| data_quality | jsonb | latest profile summary |
| schema_json | jsonb | approved physical+semantic schema |
| provenance | jsonb | import checksum, operator, filename |
| owner_id, team_id | uuid | |
| created_at / updated_at | timestamptz | |

### dataset_versions
Immutable snapshot per import: `version_number`, `record_count`, `schema_json`, `quality_json`, `object_uri`, `checksum`.

### semantic_types (field registry)
| Column | Type | Notes |
|---|---|---|
| key | text pk | `PersonName`, `Email`, … |
| physical_hint | text | default physical type |
| validation_rules | jsonb | |
| normalization_rules | jsonb | |
| analyzers | jsonb | search/index strategy |
| entity_mappings | jsonb | which entity types this field can populate |
| privacy_classification | text | `public` `pii` `sensitive` `secret` |
| is_system | bool | built-in vs admin-defined |
| created_by | uuid | |

### dataset_fields
Per-version field: `name`, `physical_type`, `semantic_type`, `confidence`, `approved`, `nullable`, `description`.

### import_jobs
`status` ∈ queued, processing, paused, failed, completed, cancelled.  
Progress: `records_processed`, `records_per_sec`, `error_count`, `invalid_count`, `duplicate_count`, `started_at`, `finished_at`, `error_message`, `wizard_state` (jsonb — steps 1–9).

### records
Phase 1 row store (bounded).  
`dataset_id`, `version_id`, `row_number`, `raw_payload jsonb` (original), `language`, `content_hash`, `duplicate_of`, `duplicate_confidence`, `duplicate_reason`.  
**Never updated in place except duplicate_* flags.**

### record_values
One row per field per record:

| Column | Type |
|---|---|
| original_value | text |
| normalized_value | text |
| canonical_value | text |
| transliterated_value | text |
| phonetic_value | text |
| language, script | text |
| is_valid | bool |
| semantic_type | text |

### entities
| Column | Type | Notes |
|---|---|---|
| id | uuid | |
| canonical_name | text | |
| entity_type | text | person, organization, username, domain, document, location, identifier |
| confidence | float | how well-supported the cluster is |
| status | text | `proposed` `active` `merged` `split` `rejected` |
| merged_into_id | uuid | |
| created_at | timestamptz | |

### entity_attributes, entity_aliases, entity_record_links
Attributes store `name`, `value`, `semantic_type`, `confidence`, `origin` (`observed`/`derived`/`inferred`/`user_confirmed`), `record_id`, `dataset_id`.  
Aliases: original + script + source.  
Links: record ↔ entity with `match_confidence` and `explain_json`.

### relationships
`from_entity_id`, `to_entity_id`, `rel_type`, `origin`, `confidence`, `evidence_id`, `source`, `discovered_at`, `created_by`.  
Never treat inferred as confirmed.

### investigations (cases)
`title`, `status` (`open` `pending` `closed`), `classification`, `owner_id`, `team_id`, `summary`.

Child tables: `investigation_items` (polymorphic: entity/record/search/relationship), `notes`, `evidence`, `timeline_events`, `saved_searches`.

### evidence
Links a fact to `record_id` / `dataset_id` / `import_job_id` / `object_uri` / `captured_at`. This is the provenance spine.

### tags / taggings
Polymorphic (`dataset`, `entity`, `record`, `investigation`).

### audit_logs
Append-only: `actor_id`, `action`, `resource_type`, `resource_id`, `ip`, `user_agent`, `payload jsonb`, `created_at`.  
Actions: login, dataset_import, dataset_view, record_view, search, entity_merge, entity_unmerge, schema_change, case_creation, permission_change, export.

### Indexes (Phase 1)

- `records (dataset_id, content_hash)`
- `record_values using gin (normalized_value gin_trgm_ops)`
- `record_values (semantic_type, canonical_value)`
- `entities (entity_type, canonical_name)`
- `audit_logs (created_at desc)`
- FTS vectors on dataset description + entity names.

---

## Scale notes

- Partition `audit_logs` and (later) `records` by month / dataset.
- Do **not** add unconstrained foreign keys from a 10B record table back to entities.
- ClickHouse order key: `(dataset_id, semantic_type, canonical_value)`.
- OpenSearch: one index per dataset version, alias `search-current`.
