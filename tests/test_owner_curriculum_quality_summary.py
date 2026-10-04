from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
MAIN=Path("crownpath/main.py").read_text(encoding="utf-8")
HTML=Path("frontend/index.html").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_quality_summary_composes_existing_read_only_checks():
    block=SERVICE.split("def curriculum_quality_summary",1)[1]
    for call in ("curriculum_progress_summary(db, user)","curriculum_structure_audit(db, user)","curriculum_readiness(db, user)","migration_readiness_dashboard(db, user)"):
        assert call in block
    assert '"read_only": True' in block


def test_quality_summary_never_executes_or_releases():
    block=SERVICE.split("def curriculum_quality_summary",1)[1]
    assert '"activation_performed": False' in block
    assert '"migration_executed": False' in block
    assert '"learner_release_authorized": False' in block
    for token in ("alembic.command","subprocess","os.system",".add(", ".delete(", ".commit("):
        assert token not in block


def test_quality_summary_route_is_owner_get_only():
    assert '@app.get("/api/owner/curriculum/quality-summary")' in MAIN
    assert '@app.post("/api/owner/curriculum/quality-summary")' not in MAIN
    assert 'Depends(require_permission("academy.manage"))' in MAIN


def test_quality_summary_ui_is_informational():
    assert 'id="loadCurriculumQuality"' in HTML
    assert "/api/owner/curriculum/quality-summary" in APP
    assert "Activation review ready" in APP
    assert "Migration" in APP


def test_quality_summary_preserves_detection_lock():
    assert "condition detection" not in (SERVICE+"\n"+MAIN+"\n"+HTML+"\n"+APP).lower()
