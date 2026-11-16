"""Synthetic audit-export approval owner binding checks."""


def claim_approval(approval, requester_id):
    if not requester_id or requester_id != approval["owner_id"]:
        return False
    if approval["used"]:
        return False
    approval["used"] = True
    return True


def test_issuing_owner_can_claim_once():
    approval = {"owner_id": "fictional-owner-a", "used": False}
    assert claim_approval(approval, "fictional-owner-a")
    assert not claim_approval(approval, "fictional-owner-a")


def test_different_owner_cannot_claim():
    approval = {"owner_id": "fictional-owner-a", "used": False}
    assert not claim_approval(approval, "fictional-owner-b")
    assert approval["used"] is False


def test_missing_requester_does_not_consume_approval():
    approval = {"owner_id": "fictional-owner-a", "used": False}
    assert not claim_approval(approval, "")
    assert approval["used"] is False
    assert claim_approval(approval, "fictional-owner-a")
