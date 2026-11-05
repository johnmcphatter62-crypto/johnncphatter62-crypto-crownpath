"""Validate the learner dashboard reflects completed classroom lessons."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User


def test_dashboard_updates_after_lesson_completion(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'dashboard.db'}")
    try:
        Base.metadata.create_all(engine)
        monkeypatch.setattr(main, "session", lambda: Session(engine))
        learner = {"user_id": "dashboard-learner", "role": "COSMETOLOGY_PRO"}
        with Session(engine) as db:
            db.add(User(user_id="dashboard-learner", name="Dashboard Learner",
                        email="dashboard-learner@example.invalid",
                        password_hash="synthetic", role="COSMETOLOGY_PRO",
                        active=True, mfa_enabled=False))
            db.commit()
        before = main.learner_dashboard(user=learner)
        assert before["overall_progress"] == 0
        assert before["modules"][0]["status"] == "NOT_STARTED"
        lesson_id = before["modules"][0]["lesson_id"]
        completed = main.complete_lesson(lesson_id, user=learner)["lesson"]
        assert completed["status"] == "COMPLETED"
        assert completed["progress"] == 100
        after = main.learner_dashboard(user=learner)
        assert after["modules"][0]["status"] == "COMPLETED"
        assert after["modules"][0]["progress"] == 100
        assert after["overall_progress"] > 0
        assert after["next_step"] != before["next_step"]
    finally:
        engine.dispose()
