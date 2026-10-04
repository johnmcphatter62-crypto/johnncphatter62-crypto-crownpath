from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_readiness_dashboard_surfaces_full_verification_chain():
    assert "recovery_verification_packet()" in SERVICE
    assert "owner_verification_decision_gate(recovery_record=integrity)" in SERVICE
    assert '"recovery_packet": packet' in SERVICE
    assert '"verification_gate": verification_gate' in SERVICE


def test_dashboard_ui_shows_protected_statuses():
    assert "Recovery evidence packet" in APP
    assert "Owner verification decision" in APP
    assert "Migration authorization" in APP
    assert "INCOMPLETE" in APP
    assert "LOCKED" in APP


def test_status_view_does_not_supply_fake_verification_or_owner_approval():
    block=SERVICE.split("def migration_readiness_dashboard",1)[1]
    assert 'verification_status":"VERIFIED"' not in block.replace(" ","")
    assert '"approved": True' not in block
    assert '"owner_confirmed": True' not in block


def test_status_view_has_no_migration_execution_path():
    joined=(SERVICE+"\n"+APP).lower()
    for token in ("alembic.command","subprocess","os.system"):
        assert token not in joined
    assert "condition detection" not in joined
