from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
MAIN=Path("crownpath/main.py").read_text(encoding="utf-8")
HTML=Path("frontend/index.html").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_dashboard_is_owner_only_and_read_only():
    assert "def migration_readiness_dashboard" in SERVICE
    assert "require_owner(user)" in SERVICE
    assert '"read_only": True' in SERVICE
    assert '"migration_executed": False' in SERVICE
    assert '"activation_performed": False' in SERVICE
    assert '"learner_release_authorized": False' in SERVICE


def test_dashboard_composes_existing_safety_gates():
    assert "verification_record()" in SERVICE
    assert "recovery_evidence_checklist()" in SERVICE
    assert "migration_authorization_gate(verification=integrity)" in SERVICE
    assert "curriculum_readiness(db, user)" in SERVICE
    assert '"BLOCKED"' in SERVICE


def test_dashboard_api_is_get_and_owner_permission():
    assert '@app.get("/api/owner/curriculum/migration-readiness")' in MAIN
    assert 'Depends(require_permission("academy.manage"))' in MAIN


def test_workspace_has_readiness_view_without_migration_control():
    assert 'id="loadMigrationReadiness"' in HTML
    assert 'id="migrationReadiness"' in HTML
    assert "/api/owner/curriculum/migration-readiness" in APP
    assert 'id="runMigration"' not in HTML
    assert 'id="authorizeMigration"' not in HTML


def test_no_migration_activation_or_release_mutation_route():
    routes="\n".join(line.lower() for line in MAIN.splitlines() if line.startswith("@app.") and "/api/owner/curriculum" in line)
    assert '@app.post("/api/owner/curriculum/migration' not in routes
    assert '@app.post("/api/owner/curriculum/activation' not in routes
    assert "publish" not in routes
    assert "release" not in routes


def test_locked_condition_detection_not_added():
    assert "condition detection" not in (SERVICE+"\n"+MAIN+"\n"+HTML+"\n"+APP).lower()
