# Dataset Model

A **Dataset** is an imported logical collection of records with metadata, a versioned schema, a quality profile, provenance, and ACL.

## Required metadata on create

- name, description (searchable)
- category, source, source description
- dataset date, import date
- language(s), geographic scope
- version, legal/usage classification
- tags, notes

## Schema

Each field has a **physical type** (`string`, `integer`, `float`, `boolean`, `date`, `datetime`, `json`, `array`, `binary`) and a **semantic type** (see field registry). Semantic type drives validation, normalization, search, and ER.

Schema detection **proposes** mappings with confidence. The operator approves or edits. No silent destructive assumptions.

## Versioning

```
customers
 ├── v1   checksum aaa  4.8M rows
 ├── v2   checksum bbb  5.1M rows
 └── v3   checksum ccc  5.1M rows   ← current
```

Versions are immutable. Comparison is a diff of schema + quality + sample hashes, not a destructive overwrite.

## Quality profile (pre-commit)

Per dataset: record count, valid, duplicates, per-field null/unique/duplicate/invalid rates, cardinality, language/script distribution, sample values.

## Provenance

`filename`, `checksum`, `byte_size`, `importer_id`, `imported_at`, `parser`, `schema_version`.
