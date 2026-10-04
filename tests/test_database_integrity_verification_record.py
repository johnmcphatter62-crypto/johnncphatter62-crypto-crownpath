from pathlib import Path

SOURCE=Path("crownpath/database_integrity.py").read_text(encoding="utf-8")


def test_verification_record_defaults_to_unverified():
    from crownpath.database_integrity import verification_record
    record=verification_record()
    assert record["verification_status"] == "UNVERIFIED"
    assert record["verified"] is False
    assert record["record_integrity_verified"] is False
    assert record["migration_authorized"] is False
    assert record["activation_authorized"] is False
    assert record["inspection_attached"] is False


def test_inspection_does_not_self_authorize_migration():
    from crownpath.database_integrity import verification_record
    record=verification_record({
        "read_only": True,
        "core_tables_expected": 12,
        "core_tables_present": 12,
        "core_tables_missing": [],
        "alembic_version": None,
        "aggregate_counts": {"users": 1},
    })
    assert record["inspection_attached"] is True
    assert record["read_only_inspection"] is True
    assert record["core_schema_complete"] is True
    assert record["verified"] is False
    assert record["migration_authorized"] is False
    assert record["activation_authorized"] is False


def test_record_requires_recovery_and_owner_evidence():
    assert "Backup or PITR source identified" in SOURCE
    assert "Owner review recorded before any production migration" in SOURCE
    assert "does not verify restored record integrity by itself" in SOURCE


def test_verification_record_contains_no_mutation_or_execution_path():
    block=SOURCE.split("def verification_record",1)[1].lower()
    for token in ("insert ","update ","delete ","drop ","alter ","create ","alembic.command","subprocess","os.system"):
        assert token not in block
