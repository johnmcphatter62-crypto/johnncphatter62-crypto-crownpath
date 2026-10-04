from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
MAIN=Path("crownpath/main.py").read_text(encoding="utf-8")
HTML=Path("frontend/index.html").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_readiness_is_owner_only_and_read_only():
    assert "def curriculum_readiness" in SERVICE
    assert "require_owner(user)" in SERVICE
    assert '"activation_performed": False' in SERVICE
    assert '"learner_publishing_enabled": False' in SERVICE
    assert '@app.get("/api/owner/curriculum/readiness")' in MAIN


def test_readiness_checks_curriculum_hierarchy_and_approvals():
    for key in ("programs","courses","units","lessons","versions","approvals"):
        assert f'"key": "{key}"' in SERVICE
    assert "Every lesson has a saved version" in SERVICE
    assert "Every lesson has an Owner-approved version" in SERVICE


def test_owner_workspace_has_readiness_check_without_activation_control():
    assert 'id="loadCurriculumReadiness"' in HTML
    assert 'id="curriculumReadiness"' in HTML
    assert "/api/owner/curriculum/readiness" in APP
    assert "does not activate curriculum or open learner access" in (HTML+"\n"+APP).lower()
    assert 'id="activateCurriculum"' not in HTML


def test_no_publish_release_or_activation_route_added():
    routes="\n".join(line.lower() for line in MAIN.splitlines() if line.startswith("@app.") and "/api/owner/curriculum" in line)
    assert "publish" not in routes
    assert "release" not in routes
    assert "/activate" not in routes


def test_locked_condition_detection_not_added():
    assert "condition detection" not in (SERVICE+"\n"+MAIN+"\n"+HTML+"\n"+APP).lower()
