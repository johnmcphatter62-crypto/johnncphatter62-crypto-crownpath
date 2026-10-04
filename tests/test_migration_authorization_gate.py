from pathlib import Path

SOURCE=Path("crownpath/database_integrity.py").read_text(encoding="utf-8")


def test_gate_is_locked_by_default():
    from crownpath.database_integrity import migration_authorization_gate
    result=migration_authorization_gate()
    assert result["status"] == "LOCKED"
    assert result["migration_authorized"] is False
    assert result["migration_executed"] is False
    assert result["activation_authorized"] is False
    assert result["learner_release_authorized"] is False


def test_owner_approval_alone_cannot_unlock_gate():
    from crownpath.database_integrity import migration_authorization_gate
    result=migration_authorization_gate(owner_authorization={
        "approved": True,
        "owner_id": "owner-1",
        "approved_at": "2026-10-04T00:00:00Z",
    })
    assert result["status"] == "LOCKED"
    assert "Restored-database recovery evidence is not verified." in result["blockers"]


def test_recovery_verification_alone_cannot_unlock_gate():
    from crownpath.database_integrity import migration_authorization_gate
    result=migration_authorization_gate(verification={
        "verified": True,
        "record_integrity_verified": True,
    })
    assert result["status"] == "LOCKED"
    assert "Explicit Owner migration authorization is not recorded." in result["blockers"]


def test_both_requirements_only_authorize_not_execute():
    from crownpath.database_integrity import migration_authorization_gate
    result=migration_authorization_gate(
        verification={"verified": True, "record_integrity_verified": True},
        owner_authorization={"approved": True, "owner_id": "owner-1", "approved_at": "2026-10-04T00:00:00Z"},
    )
    assert result["status"] == "AUTHORIZED"
    assert result["migration_authorized"] is True
    assert result["migration_executed"] is False
    assert result["activation_authorized"] is False
    assert result["learner_release_authorized"] is False


def test_gate_contains_no_migration_execution_path():
    block=SOURCE.split("def migration_authorization_gate",1)[1].lower()
    for token in ("alembic.command","upgrade(","subprocess","os.system","insert ","update ","delete ","drop ","alter ","create "):
        assert token not in block
