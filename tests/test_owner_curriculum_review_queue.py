from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
MAIN=Path("crownpath/main.py").read_text(encoding="utf-8")
HTML=Path("frontend/index.html").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_review_queue_is_owner_read_only():
    block=SERVICE.split("def curriculum_review_queue",1)[1]
    assert "require_owner(user)" in block
    assert '"read_only": True' in block
    assert '"READY_FOR_REVIEW"' in block
    assert '"CONTENT_NEEDED"' in block


def test_review_queue_only_contains_unapproved_lessons():
    block=SERVICE.split("def curriculum_review_queue",1)[1]
    assert "approved_lesson_ids" in block
    assert "if lesson.id in approved_lesson_ids" in block
    assert '"queue_count"' in block


def test_review_queue_never_executes_or_releases():
    block=SERVICE.split("def curriculum_review_queue",1)[1]
    assert '"activation_performed": False' in block
    assert '"migration_executed": False' in block
    assert '"learner_release_authorized": False' in block
    for token in ("alembic.command","subprocess","os.system",".add(", ".delete(", ".commit("):
        assert token not in block


def test_review_queue_route_is_get_only():
    assert '@app.get("/api/owner/curriculum/review-queue")' in MAIN
    assert '@app.post("/api/owner/curriculum/review-queue")' not in MAIN
    assert 'Depends(require_permission("academy.manage"))' in MAIN


def test_review_queue_ui_and_detection_lock():
    assert 'id="loadReviewQueue"' in HTML
    assert "/api/owner/curriculum/review-queue" in APP
    assert "condition detection" not in (SERVICE+"\n"+MAIN+"\n"+HTML+"\n"+APP).lower()
