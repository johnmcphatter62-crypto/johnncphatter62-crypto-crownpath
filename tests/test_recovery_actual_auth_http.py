"""Actual CrownPath HTTP authentication boundary for recovery-plan access.

Disposable SQLite users and real application cookie/session validation.
This does not add a recovery audit endpoint.
"""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import crownpath.audit as audit
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_recovery_plan_requires_real_owner_session(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'recovery_auth_http.db'}",
        connect_args={"check_same_thread": False},
    )
    for module in (auth, audit, main):
        monkeypatch.setattr(module, "session", lambda: Session(engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-recovery-http-key")
    password = "SyntheticPassword!2026"
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            for user_id, role in (("fictional-owner", "OWNER"),
                                  ("fictional-learner", "COSMETOLOGY_PRO")):
                db.add(User(
                    user_id=user_id, name=user_id,
                    email=f"{user_id}@example.com",
                    password_hash=auth.hash_password(password),
                    role=role, active=True, mfa_enabled=False,
                ))
            db.commit()
        monkeypatch.setenv("CROWNPATH_LEARNER_ACCESS_APPROVED", "true")
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            assert client.get("/api/release/recovery-plan").status_code == 401
            owner_login = client.post("/api/auth/login", json={
                "email": "fictional-owner@example.com", "password": password,
            })
            assert owner_login.status_code == 200, owner_login.text
            assert client.get("/api/release/recovery-plan").status_code == 200
            client.post("/api/auth/logout")
            assert client.get("/api/release/recovery-plan").status_code == 401
            learner_login = client.post("/api/auth/login", json={
                "email": "fictional-learner@example.com", "password": password,
            })
            assert learner_login.status_code == 200, learner_login.text
            assert client.get("/api/release/recovery-plan").status_code == 403
    finally:
        engine.dispose()
