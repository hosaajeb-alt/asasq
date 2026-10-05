# Search Document Schema

Search documents are **projections**. They are not authoritative.

```json
{
  "doc_id": "uuid",
  "dataset_id": "uuid",
  "dataset_version": "v3",
  "record_id": "uuid",
  "entity_id": "uuid|null",
  "entity_type": "person",
  "semantic_type": "PersonName",
  "field_name": "full_name",
  "original_text": "محمّد رضایی",
  "normalized_text": "محمد رضایی",
  "canonical_text": "محمد رضایی",
  "transliteration": ["Mohammad Rezaei", "Muhammad Rezaee"],
  "phonetic_key": ["MHMT", "RSY"],
  "language": "fa",
  "script": "Arab",
  "tokens": ["محمد", "رضایی", "mohammad", "rezaei"],
  "attributes": { "email": "m.rezaei@example.com" },
  "classification": "internal",
  "source_confidence": 0.92,
  "indexed_at": "2026-10-05T00:00:00Z"
}
```

## Query pipeline

```
User query
  → language detection
  → normalization (per detected + user UI locale)
  → query expansion (transliterations, phonetic keys, n-grams)
  → parallel: exact | normalized | prefix | fuzzy | phonetic | transliteration
  → ACL filter (dataset + classification)
  → candidate ranking (configurable weights)
  → explain
```

## Ranking (application layer)

```
score =
  w_exact * exact
+ w_norm  * normalized
+ w_tr    * transliteration
+ w_ph    * phonetic
+ w_attr  * attribute
+ w_ctx   * context (same dataset / case / geo)
+ w_src   * source_confidence
```

Presets: `exact`, `high_precision`, `balanced`, `broad`. Weights are admin-configurable. The UI shows **why** a hit ranked.

Phase 1 executes this against PostgreSQL. Phase 3 swaps the candidate generator for OpenSearch with the same ranker interface.
