from pathlib import Path

HTML=Path("frontend/index.html").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_owner_review_panel_is_present():
    assert 'id="curriculumReviewPanel"' in HTML
    assert 'id="curriculumReviewLesson"' in HTML
    assert 'id="curriculumVersionList"' in HTML


def test_review_uses_owner_only_version_endpoints():
    assert "/api/owner/curriculum/lessons/" in APP
    assert "/api/owner/curriculum/lesson-versions/approve" in APP


def test_approval_message_preserves_publish_boundary():
    assert "It has not been published to learners." in APP
    assert "Learner publishing remains disabled." in HTML


def test_review_workspace_adds_no_publish_or_release_api():
    relevant="\n".join(line.lower() for line in APP.splitlines() if "/api/owner/curriculum" in line)
    assert "/publish" not in relevant
    assert "/release" not in relevant


def test_locked_condition_detection_not_added():
    assert "condition detection" not in (HTML+"\n"+APP).lower()
