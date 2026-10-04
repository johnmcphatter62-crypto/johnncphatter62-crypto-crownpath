from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
MAIN=Path("crownpath/main.py").read_text(encoding="utf-8")
HTML=Path("frontend/index.html").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_approval_coverage_is_owner_read_only():
    block=SERVICE.split("def curriculum_approval_coverage",1)[1]
    assert "require_owner(user)" in block
    assert '"read_only": True' in block
    for key in ('"programs"', '"courses"', '"units"', '"missing_approval"'):
        assert key in block


def test_approval_coverage_never_executes_or_releases():
    block=SERVICE.split("def curriculum_approval_coverage",1)[1]
    assert '"activation_performed": False' in block
    assert '"migration_executed": False' in block
    assert '"learner_release_authorized": False' in block
    for token in ("alembic.command","subprocess","os.system",".add(", ".delete(", ".commit("):
        assert token not in block


def test_approval_coverage_route_is_get_only():
    assert '@app.get("/api/owner/curriculum/approval-coverage")' in MAIN
    assert '@app.post("/api/owner/curriculum/approval-coverage")' not in MAIN
    assert 'Depends(require_permission("academy.manage"))' in MAIN


def test_approval_coverage_ui_is_informational():
    assert 'id="loadApprovalCoverage"' in HTML
    assert "/api/owner/curriculum/approval-coverage" in APP
    assert "Missing approval" in APP


def test_approval_coverage_preserves_detection_lock():
    assert "condition detection" not in (SERVICE+"\n"+MAIN+"\n"+HTML+"\n"+APP).lower()
