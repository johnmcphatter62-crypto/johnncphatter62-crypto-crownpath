from pathlib import Path

SERVICE=Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")
MAIN=Path("crownpath/main.py").read_text(encoding="utf-8")


def test_duplicate_approval_is_rejected():
    assert 'if item.approved:' in SERVICE
    assert 'raise ValueError("Lesson version is already approved.")' in SERVICE


def test_only_draft_lessons_can_receive_approval():
    assert 'if lesson.status != DRAFT_STATUS:' in SERVICE
    assert 'raise ValueError("Only draft lessons can receive version approval.")' in SERVICE


def test_approval_selects_active_version_before_commit():
    active=SERVICE.index("lesson.active_version = item.version")
    audit=SERVICE.index("db.add(AuditEvent(", active)
    commit=SERVICE.index("db.commit()", audit)
    assert active < audit < commit


def test_approval_still_records_audit_event():
    assert 'action="CURRICULUM_LESSON_VERSION_APPROVED"' in SERVICE


def test_governance_adds_no_publish_or_release_routes():
    routes="\n".join(line.lower() for line in MAIN.splitlines() if line.startswith("@app.") and "/api/owner/curriculum" in line)
    assert "publish" not in routes
    assert "release" not in routes


def test_locked_condition_detection_not_added():
    assert "condition detection" not in (SERVICE+"\n"+MAIN).lower()
