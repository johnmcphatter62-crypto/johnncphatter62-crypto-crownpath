from pathlib import Path

SOURCE=Path("crownpath/database_integrity.py").read_text(encoding="utf-8")


def test_recovery_checklist_never_self_authorizes():
    from crownpath.database_integrity import recovery_evidence_checklist
    result=recovery_evidence_checklist()
    assert result["review_only"] is True
    assert result["verification_status"] == "UNVERIFIED"
    assert result["migration_authorized"] is False
    assert result["activation_authorized"] is False


def test_recovery_checklist_preserves_separate_restore_rule():
    from crownpath.database_integrity import recovery_evidence_checklist
    result=recovery_evidence_checklist()
    sequence=" ".join(result["required_sequence"]).lower()
    assert "separate database or service" in sequence
    assert "read-only integrity inspection" in sequence
    assert "owner verification decision separately" in sequence


def test_attached_inspection_only_marks_observed_evidence():
    from crownpath.database_integrity import recovery_evidence_checklist
    result=recovery_evidence_checklist({
        "read_only": True,
        "core_tables_expected": 12,
        "core_tables_present": 12,
        "core_tables_missing": [],
        "aggregate_counts": {"users": 1},
    })
    statuses={item["key"]:item["status"] for item in result["checks"]}
    assert statuses["read_only_inspection"] == "PRESENT"
    assert statuses["core_schema"] == "PRESENT"
    assert result["migration_authorized"] is False


def test_checklist_contains_no_mutation_execution_path():
    block=SOURCE.split("def recovery_evidence_checklist",1)[1].lower()
    for token in ("insert ","update ","delete ","drop ","alter ","create ","alembic.command","subprocess","os.system"):
        assert token not in block
