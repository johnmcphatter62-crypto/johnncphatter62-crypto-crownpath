"""Synthetic instructor can view academy but cannot manage Owner-only settings."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import crownpath.audit as audit
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_instructor_allowed_academy_but_denied_owner_security(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'instructor_permission_http.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    monkeypatch.setattr(audit, "session", lambda: Session(engine))
    monkeypatch.setattr(main, "session", lambda: Session(engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-instructor-permissions-key")
    monkeypatch.setattr(main, "role_access_approved", lambda role: True)
    password = "SyntheticPassword!2026"
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="synthetic-instructor", name="Synthetic Instructor",
                email="instructor-permissions@example.com",
                password_hash=auth.hash_password(password),
                role="INSTRUCTOR", active=True, mfa_enabled=False,
            ))
            db.add(User(
                user_id="synthetic-target", name="Synthetic Target",
                email="instructor-target@example.com",
                password_hash=auth.hash_password(password),
                role="BARBER", active=True, mfa_enabled=False,
            ))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "instructor-permissions@example.com", "password": password,
            })
            assert login.status_code == 200, login.text
            academy = client.get("/api/academy")
            assert academy.status_code == 200, academy.text
            assert client.get("/api/owner/users").status_code == 403
            assert client.get("/api/production/readiness").status_code == 403
            assert client.patch(
                "/api/owner/users/synthetic-target/role",
                json={"role": "INSTRUCTOR", "active": True},
            ).status_code == 403
            assert client.patch(
                "/api/owner/users/synthetic-target/active",
                json={"active": False},
            ).status_code == 403
        with Session(engine) as db:
            target = db.get(User, "synthetic-target")
            assert target.role == "BARBER"
            assert target.active is True
    finally:
        engine.dispose()
