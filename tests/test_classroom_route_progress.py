"""Exercise classroom route functions with isolated SQLite and a synthetic learner."""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import crownpath.main as main
from crownpath.db_engine import Base
from crownpath.models import User, LearnerProgress


def test_classroom_open_step_and_saved_progress(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'route_progress.db'}")
    try:
        Base.metadata.create_all(engine)
        monkeypatch.setattr(main, "session", lambda: Session(engine))
        learner = {"user_id": "route-learner", "role": "COSMETOLOGY_PRO"}
        with Session(engine) as db:
            db.add(User(user_id="route-learner", name="Route Learner",
                        email="route-learner@example.invalid",
                        password_hash="synthetic", role="COSMETOLOGY_PRO",
                        active=True, mfa_enabled=False))
            db.commit()
        opened = main.open_lesson("cosmetology-foundations", user=learner)["lesson"]
        assert opened["progress"] == 0
        assert opened["total_steps"] > 0
        completed = main.complete_lesson_step(
            "cosmetology-foundations", 1, user=learner)["lesson"]
        assert completed["completed_steps"] == [1]
        assert completed["progress"] > 0
        reopened = main.open_lesson("cosmetology-foundations", user=learner)["lesson"]
        assert reopened["completed_steps"] == [1]
        assert reopened["progress"] == completed["progress"]
        with Session(engine) as db:
            saved = db.query(LearnerProgress).filter_by(
                user_id="route-learner", lesson_id="cosmetology-foundations").one()
            assert saved.progress_percent == reopened["progress"]
        with pytest.raises(HTTPException) as denied:
            main.open_lesson("barber-foundations", user=learner)
        assert denied.value.status_code == 404
    finally:
        engine.dispose()
