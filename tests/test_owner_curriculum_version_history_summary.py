from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
MAIN=Path("crownpath/main.py").read_text(encoding="utf-8")
HTML=Path("frontend/index.html").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_version_history_is_owner_read_only():
    block=SERVICE.split("def curriculum_version_history_summary",1)[1]
    assert "require_owner(user)" in block
    assert '"read_only": True' in block
    assert '"VERSION_HISTORY_AVAILABLE"' in block


def test_version_history_reports_expected_counts():
    block=SERVICE.split("def curriculum_version_history_summary",1)[1]
    for field in ('"saved_versions"','"approved_versions"','"unapproved_versions"','"lessons_with_multiple_versions"','"revised_lessons"'):
        assert field in block


def test_version_history_never_executes_or_releases():
    block=SERVICE.split("def curriculum_version_history_summary",1)[1]
    assert '"activation_performed": False' in block
    assert '"migration_executed": False' in block
    assert '"learner_release_authorized": False' in block
    for token in ("alembic.command","subprocess","os.system",".add(", ".delete(", ".commit("):
        assert token not in block


def test_version_history_route_is_get_only():
    assert '@app.get("/api/owner/curriculum/version-history-summary")' in MAIN
    assert '@app.post("/api/owner/curriculum/version-history-summary")' not in MAIN
    assert 'Depends(require_permission("academy.manage"))' in MAIN


def test_version_history_ui_and_detection_lock():
    assert 'id="loadVersionHistory"' in HTML
    assert "/api/owner/curriculum/version-history-summary" in APP
    assert "condition detection" not in (SERVICE+"\n"+MAIN+"\n"+HTML+"\n"+APP).lower()
