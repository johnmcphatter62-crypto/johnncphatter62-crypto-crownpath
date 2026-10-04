from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
MAIN=Path("crownpath/main.py").read_text(encoding="utf-8")
HTML=Path("frontend/index.html").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_activation_plan_is_preview_only():
    assert "def activation_plan_preview" in SERVICE
    assert '"preview_only": True' in SERVICE
    assert '"activation_performed": False' in SERVICE
    assert '"migration_performed": False' in SERVICE
    assert '"learner_release_performed": False' in SERVICE


def test_activation_plan_preserves_recovery_gate():
    assert "Verify backup and restored-database integrity" in SERVICE
    assert "Restored-database record integrity has not been independently verified." in SERVICE
    assert "Production curriculum migration has not been applied." in SERVICE


def test_activation_plan_requires_separate_learner_release_decision():
    assert "separate Owner-approved release gate" in SERVICE
    assert "Learner release requires a separate future Owner approval." in SERVICE


def test_preview_api_is_get_and_owner_only():
    assert '@app.get("/api/owner/curriculum/activation-plan")' in MAIN
    assert 'Depends(require_permission("academy.manage"))' in MAIN


def test_workspace_has_preview_not_activation_control():
    assert 'id="loadCurriculumActivationPlan"' in HTML
    assert 'id="curriculumActivationPlan"' in HTML
    assert "/api/owner/curriculum/activation-plan" in APP
    assert 'id="activateCurriculum"' not in HTML


def test_no_activation_publish_or_release_mutation_route():
    routes="\n".join(line.lower() for line in MAIN.splitlines() if line.startswith("@app.") and "/api/owner/curriculum" in line)
    assert '@app.post("/api/owner/curriculum/activation' not in routes
    assert "publish" not in routes
    assert "release" not in routes


def test_locked_condition_detection_not_added():
    assert "condition detection" not in (SERVICE+"\n"+MAIN+"\n"+HTML+"\n"+APP).lower()
