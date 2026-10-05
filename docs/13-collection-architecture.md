# Collection-centric architecture

A **Collection** is a first-class domain object. It is not a tag, a dataset field, or a UI filter.

```
Workspace
  → Collection
      → Dataset
          → Record
              → Entity (may span collections)
                  → Evidence
```

All ingestion, search (text / metadata / vector / face), entity resolution, graph, investigations, permissions, audit, lifecycle, retention, index rebuilds, quality, and export are **Collection-scoped**.

## Rules

1. Every imported record has Collection provenance. There is no global namespace import.
2. A Dataset belongs to **exactly one** primary Collection. Controlled multi-collection *references* (e.g. entity `observed_in`) are separate from ownership.
3. Collection filtering happens in the **router**, before index fan-out — never “search everything then filter.”
4. Physical storage may be shared (logical partition / alias / namespace) or dedicated. One physical database per Collection is **not** required.
5. Rebuilding one Collection must not rebuild the platform.
6. Source names (any site, registry, or feed) are **user configuration**, never `if source == "…"`.
7. Face / vector hits are **candidates for human review**, never identity.
8. Original values remain immutable. Collection policies only affect derived forms.

## Search routing

```
Request → authz → Collection Scope Resolver
       → Collection Index Router (only selected collections)
       → text / metadata / vector / face / graph (per index policy)
       → merge → rank → dedup → ER proposals → results
```

Global search is `scope.collections = ["*"]` **intersected with collections the principal may search**.

## Indexes (logical)

Each Collection may enable:

`text` · `metadata` · `vector` · `face` · `entity` · `graph`

Provisioned from `index_policy`. Phase 1: PostgreSQL/SQLite projections partitioned by `collection_id`. Phase 3+: OpenSearch aliases + vector engine (HNSW/IVF) behind `FaceEmbeddingStore`.

## Face search

```
image → detect → quality → align → embed
     → Collection scope → FaceEmbeddingStore.search(collection_ids)
     → top-k → metadata filter → optional rerank → human review
```

`FaceEmbeddingStore` is an interface (`insert`, `batch_insert`, `search`, `rebuild_index`, …). Phase 1 uses a collection-filtered cosine store. Scale path: sharded HNSW / IVF-PQ, never brute-force global comparison.

## Dedup scopes

`dataset` · `collection` · `cross-collection` · `entity` · `global`

Auto-merge is off by default. Decisions store `duplicate_of`, scores, method, confidence, review_status, provenance.

## Isolation

Authorization is enforced server-side on every path (search, suggest, graph, export, jobs). Inaccessible collections must not leak through autocomplete, analytics, or embeddings.
