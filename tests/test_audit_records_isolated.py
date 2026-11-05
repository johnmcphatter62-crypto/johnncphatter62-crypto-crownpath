"""Audit persistence and ordering in disposable SQLite only.

This tests the audit storage helper, not whether every authentication route
emits an event. Route-level security audit coverage remains a release gap.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import crownpath.audit as audit
from crownpath.db_engine import Base
from crownpath.models import AuditEvent


def test_synthetic_security_audit_records_are_ordered_and_limited(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'synthetic_audit.db'}")
    monkeypatch.setattr(audit, "session", lambda: Session(engine))
    try:
        Base.metadata.create_all(engine)
        audit.record_audit(
            user_id="synthetic-owner",
            action="SYNTHETIC_LOGIN_DENIED",
            category="SECURITY",
            result="DENIED",
            reason="Invalid credentials (no password recorded)",
        )
        audit.record_audit(
            user_id="synthetic-owner",
            action="SYNTHETIC_ACCOUNT_LOCKED",
            category="SECURITY",
            result="DENIED",
            reason="Lockout threshold reached",
        )
        recent = audit.recent_audit(limit=1)
        assert len(recent) == 1
        assert recent[0]["action"] == "SYNTHETIC_ACCOUNT_LOCKED"
        assert recent[0]["user_id"] == "synthetic-owner"
        with Session(engine) as db:
            records = db.query(AuditEvent).order_by(AuditEvent.audit_id).all()
            assert [r.action for r in records] == [
                "SYNTHETIC_LOGIN_DENIED", "SYNTHETIC_ACCOUNT_LOCKED"
            ]
            assert all(r.category == "SECURITY" for r in records)
    finally:
        engine.dispose()
