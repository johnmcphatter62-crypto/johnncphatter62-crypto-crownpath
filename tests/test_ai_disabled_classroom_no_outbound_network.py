"""Offline CrownPath classroom HTTP route test with network blocked.

Uses synthetic auth and disposable SQLite. Socket connections are blocked only
after TestClient startup, so this test checks essential request handling rather
than deployment startup behavior. No live student or provider access.
"""
import socket
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_classroom_routes_do_not_need_outbound_network(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'no_network.db'}",
                           connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(engine)
        monkeypatch.setattr(auth, "session", lambda: Session(engine))
        monkeypatch.setattr(main, "session", lambda: Session(engine))
        monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-no-network-key")
        monkeypatch.setenv("CROWNPATH_LEARNER_ACCESS_APPROVED", "true")
        monkeypatch.setenv("CROWNPATH_AI_ENABLED", "false")
        with Session(engine) as db:
            db.add(User(user_id="no-network-learner", name="No Network Learner",
                        email="no-network-learner@example.com",
                        password_hash=auth.hash_password("SyntheticPassword!2026"),
                        role="COSMETOLOGY_PRO", active=True, mfa_enabled=False))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            def deny_outbound(*args, **kwargs):
                raise AssertionError("Outbound network attempted during classroom request")
            monkeypatch.setattr(socket, "create_connection", deny_outbound)
            login = client.post("/api/auth/login", json={
                "email": "no-network-learner@example.com",
                "password": "SyntheticPassword!2026"})
            assert login.status_code == 200, login.text
            dashboard = client.get("/api/learner/dashboard")
            assert dashboard.status_code == 200, dashboard.text
            lesson_id = dashboard.json()["modules"][0]["lesson_id"]
            assert client.post(f"/api/learner/lessons/{lesson_id}/open").status_code == 200
            completed = client.post(
                f"/api/learner/lessons/{lesson_id}/steps/1/complete")
            assert completed.status_code == 200, completed.text
            assert 1 in completed.json()["lesson"]["completed_steps"]
            assert client.get("/api/owner/curriculum/progress-summary").status_code == 403
    finally:
        engine.dispose()
