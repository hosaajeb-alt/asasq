# Entity-Resolution Architecture

Goal: propose that two records **might** describe the same real-world entity, with an explanation, without O(n²) comparisons.

## Pipeline

```
10B records
    → blocking (normalized keys, phonetic keys, hashed identifiers)
    → candidate generation (inverted indexes, ANN where useful)
    → similarity scoring (name, translit, phonetic, attributes)
    → confidence + explanation
    → human review  OR  auto-link rules (policy)
    → entity graph
```

## Blocking (required)

A candidate pair is generated only if they share at least one block key, for example:

- exact canonical email / phone / national id / domain
- normalized name prefix + country
- phonetic key + city
- username casefold

Block keys are stored on `record_values` / a dedicated `block_keys` table (Phase 1: computed at profile/import time).

## Scoring

```
name_sim           (normalized Levenshtein / Jaro-Winkler / token Jaccard)
+ translit_sim
+ phonetic_sim     (weight low)
+ attribute_sim    (email/phone exact is strong)
```

Explain payload example:

```
✓ same normalized email
✓ similar normalized name (0.91)
✓ same city
✗ different phone
confidence: 0.96
```

## Policy

- Default: **propose only**. Analyst confirms.
- Auto-link rules are explicit, versioned, and audited (`entity_merge`).
- Name-only matches never auto-merge.
- Merges are reversible.

## Scale path

Phase 1: in-process blocking over PG.  
Phase 4+: Spark/Flink or worker pool over parquet; ANN (e.g. names in FAISS) as an additional candidate source, never the only one.
