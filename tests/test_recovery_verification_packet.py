from pathlib import Path

SOURCE=Path("crownpath/database_integrity.py").read_text(encoding="utf-8")


def test_packet_is_incomplete_and_locked_by_default():
    from crownpath.database_integrity import recovery_verification_packet
    packet=recovery_verification_packet()
    assert packet["status"] == "INCOMPLETE"
    assert packet["evidence_complete"] is False
    assert packet["verified"] is False
    assert packet["record_integrity_verified"] is False
    assert packet["migration_authorized"] is False
    assert packet["migration_executed"] is False
    assert packet["activation_authorized"] is False
    assert packet["learner_release_authorized"] is False


def test_complete_evidence_remains_unverified():
    from crownpath.database_integrity import recovery_verification_packet
    packet=recovery_verification_packet({
        "backup_source":"pitr-reference",
        "restore_target":"separate-restored-service",
        "restore_time":"recovery-target",
        "inspection_result":{"read_only":True},
        "schema_review":{"complete":True},
        "aggregate_review":{"reviewed":True},
        "restore_procedure":"documented",
        "owner_review":"pending verification decision",
    })
    assert packet["evidence_complete"] is True
    assert packet["status"] == "EVIDENCE_COMPLETE_UNVERIFIED"
    assert packet["verified"] is False
    assert packet["migration_authorized"] is False


def test_packet_requires_recovery_evidence_categories():
    from crownpath.database_integrity import recovery_verification_packet
    keys={item["key"] for item in recovery_verification_packet()["items"]}
    assert keys == {"backup_source","restore_target","restore_time","inspection_result","schema_review","aggregate_review","restore_procedure","owner_review"}


def test_packet_contains_no_execution_or_mutation_path():
    block=SOURCE.split("def recovery_verification_packet",1)[1].lower()
    for token in ("alembic.command","upgrade(","subprocess","os.system","insert ","update ","delete ","drop ","alter ","create "):
        assert token not in block
