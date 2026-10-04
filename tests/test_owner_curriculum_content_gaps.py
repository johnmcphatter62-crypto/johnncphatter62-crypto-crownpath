from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
MAIN=Path("crownpath/main.py").read_text(encoding="utf-8")
HTML=Path("frontend/index.html").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_content_gaps_is_owner_read_only():
    block=SERVICE.split("def curriculum_content_gaps",1)[1]
    assert "require_owner(user)" in block
    assert '"read_only": True' in block
    assert '"needs_content"' in block
    assert '"awaiting_approval"' in block


def test_content_gaps_separates_missing_from_unapproved():
    block=SERVICE.split("def curriculum_content_gaps",1)[1]
    assert "if not lesson_versions" in block
    assert "elif lesson.id not in approved_lesson_ids" in block
    assert '"needs_content_count"' in block
    assert '"awaiting_approval_count"' in block


def test_content_gaps_never_executes_or_releases():
    block=SERVICE.split("def curriculum_content_gaps",1)[1]
    assert '"activation_performed": False' in block
    assert '"migration_executed": False' in block
    assert '"learner_release_authorized": False' in block
    for token in ("alembic.command","subprocess","os.system",".add(", ".delete(", ".commit("):
        assert token not in block


def test_content_gaps_route_is_get_only():
    assert '@app.get("/api/owner/curriculum/content-gaps")' in MAIN
    assert '@app.post("/api/owner/curriculum/content-gaps")' not in MAIN
    assert 'Depends(require_permission("academy.manage"))' in MAIN


def test_content_gaps_ui_and_detection_lock():
    assert 'id="loadContentGaps"' in HTML
    assert "/api/owner/curriculum/content-gaps" in APP
    assert "condition detection" not in (SERVICE+"\n"+MAIN+"\n"+HTML+"\n"+APP).lower()
