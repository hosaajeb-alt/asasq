# Frontend Information Architecture

## Navigation

Dashboard · Datasets · Search · Entities · Graph · Investigations · Evidence · Data Quality · Admin

Search is the central experience. Cmd/Ctrl+K opens a command palette.

## Locale

- Languages: English (LTR), Persian (RTL). Switchable without reload.
- Messages live under `/frontend/i18n/{en,fa}/*.json` — never hardcoded in components.
- `dir` on `<html>` flips; sidebar and numeric/date formats follow locale (Persian calendar optional).
- Adding a language = add a folder of JSON files + a locale entry.

## Layout

- Dense dark intelligence workspace (not a marketing dashboard).
- Persistent sidebar, top search, status bar (connection, record counts, jobs).
- Entity profile and dataset pages use stacked tabs, not sparse cards.
- Inferred vs observed is color-coded everywhere.

## Import wizard (9 steps)

1. Upload  2. Dataset information  3. Schema detection  4. Field mapping  
5. Normalization rules  6. Data quality preview  7. Entity mapping  8. Review  9. Import

Back navigation preserves wizard state.

## Search result row

Entity/record · source dataset · match type · confidence · explain chips.

## Visual language

- Background: deep navy. Accent: amber (action) + cyan (data) + violet (graph).
- Type: IBM Plex Sans (EN) + Vazirmatn (FA). Mono for ids/hashes.
- Motion is functional (panel open, not decoration).
