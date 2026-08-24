from crownpath.permissions import has_permission

def test_owner_has_owner_dashboard():
    user={"active":True,"role":"OWNER"}
    assert has_permission(user,"dashboard.owner")

def test_inactive_user_denied():
    user={"active":False,"role":"OWNER"}
    assert not has_permission(user,"dashboard.owner")
