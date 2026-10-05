# Normalization Architecture

Normalization is **language-aware**, **reversible from a provenance perspective**, and **never destructive**.

## Value envelope

Every processed cell becomes:

```
original_value          # byte-for-byte / Unicode as imported
normalized_value        # language module output (matching form)
canonical_value         # registry canonical (e.g. lowercased email)
transliterated_value    # Latin (or requested script) — may be many
phonetic_value          # matching key, not display
language, script
```

The original is always shown in the UI and stored.

## Module dispatch

```
semantic_type + language  →  Normalizer.normalize(value) -> Envelope
```

There is **no** single Unicode NFKC pass that is applied to every language as the only step. A shared Unicode hygiene step (NFC, strip tag characters) runs first; language modules then apply their own rules.

## Language modules (Phase 1 implemented)

| Module | Responsibilities |
|---|---|
| `persian` | ی/ي/ى, ک/ك, diacritics, tatweel, ZWNJ policy, presentation forms, alef variants |
| `arabic` | similar letter folding with Arabic yeh/kaf defaults, diacritics, tatweel |
| `turkish` | İ/I/i/ı case folding (locale-correct) |
| `kurdish` | Arabic-script Kurdish letter folding + Latin Kurmanji |
| `hebrew` | final forms, niqqud strip for matching |
| `russian` | yo/е policy, Cyrillic casefold |
| `english` | NFKC, casefold, punctuation policy for names |
| `generic` | NFC + whitespace + control-char strip |

## Transliteration

Multiple strategies may coexist (scientific, UNGEGN, colloquial). Stored separately. Example:

```
محمد → Mohammad | Muhammad | Mohamed | Mohammed
```

Never replaces the original.

## Phonetics

Used as a **ranking signal**, not identity. Latin: Double Metaphone-style keys. Persian/Arabic: consonant skeleton after normalization.

## Email / phone / domain

- Email: trim, IDNA domain, local-part case policy.
- Phone: digits + optional E.164 if region known; original kept.
- Domain: lower, strip trailing dot, Unicode punycode canonical.
