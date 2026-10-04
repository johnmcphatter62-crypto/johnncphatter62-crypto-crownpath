from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
MAIN=Path("crownpath/main.py").read_text(encoding="utf-8")
HTML=Path("frontend/index.html").read_text(encoding="utf-8")
APP=Path("frontend/app.js").read_text(encoding="utf-8")


def test_approval_records_existing_audit_event():
    assert "AuditEvent(" in SERVICE
    assert 'action="CURRICULUM_LESSON_VERSION_APPROVED"' in SERVICE
    assert 'category="CURRICULUM"' in SERVICE
    assert 'resource_type="CURRICULUM_LESSON_VERSION"' in SERVICE


def test_owner_approval_history_is_scoped():
    assert "def list_approval_history" in SERVICE
    assert 'AuditEvent.category == "CURRICULUM"' in SERVICE
    assert 'AuditEvent.action == "CURRICULUM_LESSON_VERSION_APPROVED"' in SERVICE
    assert '@app.get("/api/owner/curriculum/approval-history")' in MAIN
    assert 'Depends(require_permission("academy.manage"))' in MAIN


def test_owner_workspace_shows_approval_history():
    assert 'id="curriculumApprovalHistory"' in HTML
    assert "/api/owner/curriculum/approval-history" in APP


def test_no_publish_or_release_route_added():
    routes="\n".join(line.lower() for line in MAIN.splitlines() if line.startswith("@app.") and "/api/owner/curriculum" in line)
    assert "publish" not in routes
    assert "release" not in routes


def test_locked_condition_detection_not_added():
    assert "condition detection" not in (SERVICE+"\n"+MAIN+"\n"+HTML+"\n"+APP).lower()
