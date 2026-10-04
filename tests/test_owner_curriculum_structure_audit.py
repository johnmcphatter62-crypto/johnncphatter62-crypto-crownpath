from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
MAIN=Path("crownpath/main.py").read_text(encoding="utf-8")
HTML=Path("frontend/index.html").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_structure_audit_is_owner_only_and_read_only():
    assert "def curriculum_structure_audit" in SERVICE
    assert "require_owner(user)" in SERVICE
    assert '"read_only": True' in SERVICE
    assert '"activation_performed": False' in SERVICE
    assert '"learner_release_authorized": False' in SERVICE


def test_structure_audit_checks_expected_blockers():
    for key in ("orphaned_courses","orphaned_units","orphaned_lessons","orphaned_versions","lessons_without_approved_version","blocker_count"):
        assert f'"{key}"' in SERVICE
    assert '"CLEAR" if blockers == 0 else "REVIEW_REQUIRED"' in SERVICE


def test_structure_audit_route_is_get_only():
    assert '@app.get("/api/owner/curriculum/structure-audit")' in MAIN
    assert '@app.post("/api/owner/curriculum/structure-audit")' not in MAIN


def test_structure_audit_ui_is_informational():
    assert 'id="loadCurriculumAudit"' in HTML
    assert "/api/owner/curriculum/structure-audit" in APP
    assert "Lessons missing approval" in APP


def test_structure_audit_has_no_execution_or_release_path():
    block=SERVICE.split("def curriculum_structure_audit",1)[1]
    for token in ("alembic.command","subprocess","os.system",".add(", ".delete(", ".commit("):
        assert token not in block
    assert "condition detection" not in (SERVICE+"\n"+MAIN+"\n"+HTML+"\n"+APP).lower()
