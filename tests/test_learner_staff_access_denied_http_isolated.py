"""Learners must not manage staff accounts (synthetic HTTP + SQLite)."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import crownpath.audit as audit
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_learner_cannot_change_staff_role_or_activation(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'synthetic_denied_staff.db'}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(auth, "session", lambda: Session(engine))
    monkeypatch.setattr(audit, "session", lambda: Session(engine))
    monkeypatch.setattr(main, "session", lambda: Session(engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-denied-staff-key")
    monkeypatch.setattr(main, "role_access_approved", lambda role: True)
    password = "SyntheticPassword!2026"
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            for user_id, role in [
                ("synthetic-learner-actor", "COSMETOLOGY_PRO"),
                ("synthetic-staff-target", "BARBER"),
            ]:
                db.add(User(
                    user_id=user_id, name=user_id,
                    email=f"{user_id}@example.com",
                    password_hash=auth.hash_password(password),
                    role=role, active=True, mfa_enabled=False,
                ))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "synthetic-learner-actor@example.com",
                "password": password,
            })
            assert login.status_code == 200, login.text
            role = client.patch(
                "/api/owner/users/synthetic-staff-target/role",
                json={"role": "INSTRUCTOR", "active": True},
            )
            active = client.patch(
                "/api/owner/users/synthetic-staff-target/active",
                json={"active": False},
            )
            users = client.get("/api/owner/users")
            assert role.status_code == 403, role.text
            assert active.status_code == 403, active.text
            assert users.status_code == 403, users.text
        with Session(engine) as db:
            target = db.get(User, "synthetic-staff-target")
            assert target.role == "BARBER"
            assert target.active is True
    finally:
        engine.dispose()
