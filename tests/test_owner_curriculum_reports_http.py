"""Owner-only HTTP curriculum reporting in an isolated SQLite test."""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import crownpath.auth as auth
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_owner_can_read_curriculum_reports(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'owner_reports.db'}",
                           connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(engine)
        monkeypatch.setattr(auth, "session", lambda: Session(engine))
        monkeypatch.setattr(main, "session", lambda: Session(engine))
        monkeypatch.setattr(auth, "SECRET_KEY", "isolated-owner-report-test-key")
        with Session(engine) as db:
            db.add(User(user_id="owner-test", name="Synthetic Owner",
                        email="owner-reports@example.com",
                        password_hash=auth.hash_password("SyntheticPassword!2026"),
                        role="OWNER", active=True, mfa_enabled=False))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "owner-reports@example.com",
                "password": "SyntheticPassword!2026"})
            assert login.status_code == 200, login.text
            progress = client.get("/api/owner/curriculum/progress-summary")
            assert progress.status_code == 200, progress.text
            assert progress.json()["read_only"] is True
            assert progress.json()["learner_release_authorized"] is False
            completion = client.get("/api/owner/curriculum/completion-dashboard")
            assert completion.status_code == 200, completion.text
            assert completion.json()["read_only"] is True
            assert completion.json()["activation_performed"] is False
    finally:
        engine.dispose()
