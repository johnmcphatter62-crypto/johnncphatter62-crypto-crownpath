from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
MAIN=Path("crownpath/main.py").read_text(encoding="utf-8")
HTML=Path("frontend/index.html").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_approval_backlog_is_owner_read_only():
    block=SERVICE.split("def curriculum_approval_backlog",1)[1]
    assert "require_owner(user)" in block
    assert '"read_only": True' in block
    assert '"APPROVAL_REVIEW_REQUIRED"' in block


def test_approval_backlog_reports_waiting_work():
    block=SERVICE.split("def curriculum_approval_backlog",1)[1]
    assert "approved_lesson_ids" in block
    assert '"backlog_count"' in block
    assert '"saved_versions_waiting"' in block
    assert '"backlog"' in block


def test_approval_backlog_never_executes_or_releases():
    block=SERVICE.split("def curriculum_approval_backlog",1)[1]
    assert '"activation_performed": False' in block
    assert '"migration_executed": False' in block
    assert '"learner_release_authorized": False' in block
    for token in ("alembic.command","subprocess","os.system",".add(", ".delete(", ".commit("):
        assert token not in block


def test_approval_backlog_route_is_get_only():
    assert '@app.get("/api/owner/curriculum/approval-backlog")' in MAIN
    assert '@app.post("/api/owner/curriculum/approval-backlog")' not in MAIN
    assert 'Depends(require_permission("academy.manage"))' in MAIN


def test_approval_backlog_ui_and_detection_lock():
    assert 'id="loadApprovalBacklog"' in HTML
    assert "/api/owner/curriculum/approval-backlog" in APP
    assert "condition detection" not in (SERVICE+"\n"+MAIN+"\n"+HTML+"\n"+APP).lower()
