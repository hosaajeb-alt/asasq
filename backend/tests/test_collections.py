from app.core.access import Principal, Resource, SEARCH, VIEW, evaluate
from app.vector.face import embed_seed, run_pipeline
from app.vector.store import _cosine


def test_cosine_identical():
    v = embed_seed("same-person-seed")
    assert _cosine(v, v) > 0.99


def test_cosine_distinct():
    a = embed_seed("family-a")
    b = embed_seed("family-b")
    assert _cosine(a, b) < 0.99


def test_pipeline_never_asserts_identity():
    out = run_pipeline(b"fake-image-bytes-0123456789")
    assert out["identity_asserted"] is False
    assert out["vector"]
    assert 0 <= out["quality"] <= 1


def test_empty_collection_scope_does_not_search_global():
    # Router contract: no authorized collections → no results, not a global scan.
    class FakeDB:
        def query(self, *_a, **_k):
            raise AssertionError("must not query embeddings when collection_ids is empty")

    from app.vector.store import InAppFaceStore

    store = InAppFaceStore(FakeDB())  # type: ignore[arg-type]
    assert store.search([0.1] * 4, [], top_k=10) == []
    assert _cosine([], [0.1]) == 0.0


def test_viewer_cannot_export_restricted_collection():
    p = Principal(user_id="u1", role="viewer")
    r = Resource(type="collection", id="c1", classification="restricted", owner_id="other")
    assert evaluate(p, VIEW, r) is False
    assert evaluate(p, SEARCH, r) is False
