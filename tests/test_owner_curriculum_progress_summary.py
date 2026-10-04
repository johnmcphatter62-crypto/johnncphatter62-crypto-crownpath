from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
MAIN=Path("crownpath/main.py").read_text(encoding="utf-8")
HTML=Path("frontend/index.html").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_progress_summary_is_owner_only_and_read_only():
    assert "def curriculum_progress_summary" in SERVICE
    assert "require_owner(user)" in SERVICE
    assert '"read_only": True' in SERVICE
    assert '"activation_performed": False' in SERVICE
    assert '"learner_release_authorized": False' in SERVICE


def test_progress_summary_counts_hierarchy_and_approvals():
    for key in ("programs","courses","units","lessons","saved_versions","approved_versions","lessons_with_approved_version","lessons_waiting_for_approval"):
        assert f'"{key}"' in SERVICE


def test_progress_summary_route_is_owner_get_only():
    assert '@app.get("/api/owner/curriculum/progress-summary")' in MAIN
    assert 'Depends(require_permission("academy.manage"))' in MAIN
    assert '@app.post("/api/owner/curriculum/progress-summary")' not in MAIN


def test_progress_summary_ui_is_informational():
    assert 'id="loadCurriculumProgress"' in HTML
    assert 'id="curriculumProgress"' in HTML
    assert "/api/owner/curriculum/progress-summary" in APP
    assert "Lessons waiting for approval" in APP


def test_progress_summary_does_not_add_release_or_migration_execution():
    joined=(SERVICE+"\n"+MAIN+"\n"+HTML+"\n"+APP).lower()
    assert "condition detection" not in joined
    block=SERVICE.split("def curriculum_progress_summary",1)[1]
    for token in ("alembic.command","subprocess","os.system"):
        assert token not in block
