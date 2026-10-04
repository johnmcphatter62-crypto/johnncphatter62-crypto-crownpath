from pathlib import Path

SOURCE=Path("crownpath/database_integrity.py").read_text(encoding="utf-8")


def test_decision_gate_locked_by_default():
    from crownpath.database_integrity import owner_verification_decision_gate
    result=owner_verification_decision_gate()
    assert result["status"] == "LOCKED"
    assert result["verification_accepted"] is False
    assert result["migration_authorized"] is False
    assert result["migration_executed"] is False


def test_owner_signoff_cannot_manufacture_verification():
    from crownpath.database_integrity import owner_verification_decision_gate
    result=owner_verification_decision_gate(
        owner_decision={"decision":"VERIFY_RECOVERY","owner_confirmed":True,"owner_id":"owner-1","decided_at":"2026-10-04T00:00:00Z"}
    )
    assert result["status"] == "LOCKED"
    assert result["record_integrity_verified"] is False


def test_verified_record_without_owner_signoff_stays_locked():
    from crownpath.database_integrity import owner_verification_decision_gate
    result=owner_verification_decision_gate(
        recovery_record={"verification_status":"VERIFIED","verified":True,"record_integrity_verified":True}
    )
    assert result["status"] == "LOCKED"
    assert result["owner_signoff_present"] is False


def test_verified_record_plus_owner_signoff_accepts_verification_only():
    from crownpath.database_integrity import owner_verification_decision_gate
    result=owner_verification_decision_gate(
        recovery_record={"verification_status":"VERIFIED","verified":True,"record_integrity_verified":True},
        owner_decision={"decision":"VERIFY_RECOVERY","owner_confirmed":True,"owner_id":"owner-1","decided_at":"2026-10-04T00:00:00Z"},
    )
    assert result["status"] == "VERIFIED"
    assert result["verification_accepted"] is True
    assert result["migration_authorized"] is False
    assert result["migration_executed"] is False
    assert result["activation_authorized"] is False
    assert result["learner_release_authorized"] is False


def test_gate_has_no_execution_or_mutation_path():
    block=SOURCE.split("def owner_verification_decision_gate",1)[1].lower()
    for token in ("alembic.command","upgrade(","subprocess","os.system","insert ","update ","delete ","drop ","alter ","create "):
        assert token not in block
