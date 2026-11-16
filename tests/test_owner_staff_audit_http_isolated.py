"""Synthetic Owner staff-change audit HTTP checks in disposable SQLite."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import crownpath.audit as audit
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import AuditEvent, User


def test_owner_staff_changes_generate_audit_events(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'synthetic_staff_audit.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    monkeypatch.setattr(audit, "session", lambda: Session(engine))
    monkeypatch.setattr(main, "session", lambda: Session(engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-staff-audit-key")
    password = "SyntheticPassword!2026"
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="synthetic-owner", name="Synthetic Owner",
                email="staff-audit-owner@example.com",
                password_hash=auth.hash_password(password),
                role="OWNER", active=True, mfa_enabled=False,
            ))
            db.add(User(
                user_id="synthetic-learner", name="Synthetic Learner",
                email="staff-audit-learner@example.com",
                password_hash=auth.hash_password(password),
                role="COSMETOLOGY_PRO", active=True, mfa_enabled=False,
            ))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "staff-audit-owner@example.com", "password": password,
            })
            assert login.status_code == 200, login.text
            role = client.patch("/api/owner/users/synthetic-learner/role", json={
                "role": "BARBER", "active": True,
            })
            assert role.status_code == 200, role.text
            active = client.patch("/api/owner/users/synthetic-learner/active", json={
                "active": False,
            })
            assert active.status_code == 200, active.text
        with Session(engine) as db:
            events = db.scalars(select(AuditEvent).order_by(AuditEvent.audit_id)).all()
            staff = [event for event in events if event.action in (
                "STAFF_ROLE_UPDATED", "STAFF_ACTIVE_UPDATED"
            )]
            assert [event.action for event in staff] == [
                "STAFF_ROLE_UPDATED", "STAFF_ACTIVE_UPDATED"
            ]
            assert all(event.user_id == "synthetic-owner" for event in staff)
            assert all(event.resource_id == "synthetic-learner" for event in staff)
            assert all(event.resource_type == "USER" for event in staff)
            assert all(event.result == "SUCCESS" for event in staff)
            assert all(password not in str(event.reason) for event in staff)
    finally:
        engine.dispose()
