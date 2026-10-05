from app.core.access import ADMIN, EDIT, IMPORT, MERGE, VIEW, Principal, Resource, evaluate


def test_admin_can_everything():
    p = Principal(user_id="1", role="admin")
    assert evaluate(p, ADMIN)
    assert evaluate(p, MERGE)


def test_viewer_cannot_import_or_merge():
    p = Principal(user_id="2", role="viewer")
    assert evaluate(p, VIEW) is True
    assert evaluate(p, IMPORT) is False
    assert evaluate(p, MERGE) is False


def test_owner_can_edit_own_dataset():
    p = Principal(user_id="3", role="viewer")
    r = Resource(type="dataset", id="d", owner_id="3")
    assert evaluate(p, EDIT, r) is True


def test_restricted_not_editable_by_investigator_without_grant():
    p = Principal(user_id="4", role="investigator")
    r = Resource(type="dataset", id="d", classification="restricted", owner_id="other")
    assert evaluate(p, EDIT, r) is False
