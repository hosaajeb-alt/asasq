# Entity Model

A **Record** is a row/document from a dataset. An **Entity** is a canonical real-world object that may be supported by many records.

```
Record (dataset A)  ─┐
Record (dataset B)  ─┼─►  Entity (person: محمد رضایی)
Record (dataset C)  ─┘         │
                               ├─ aliases
                               ├─ attributes (with provenance)
                               ├─ relationships
                               └─ evidence
```

## Entity types (built-in)

`person` · `organization` · `username` · `domain` · `ip` · `email` · `document` · `location` · `identifier` · `other`

Admins may add types; they are registry entries, not hardcoded UI branches.

## Invariants

1. Creating an entity does not delete or mutate records.
2. Linking a record to an entity is an evidence-bearing event (`entity_record_links.explain_json`).
3. Name equality never auto-merges. A merge requires either a matching rule (e.g. same normalized email + similar name, threshold ≥ τ) **and** policy allow, or a human decision.
4. `merged` entities point at `merged_into_id`. Unmerge restores links.
5. Every attribute has `origin`: `observed | derived | inferred | user_confirmed`.
6. Confidence is a score in `[0,1]`, never a boolean.

## Profile (UI)

Overview · Attributes · Relationships · Evidence · Timeline · Sources

Fields: canonical name, aliases, type, confidence, attributes, source records, related entities, datasets, cases.
