"""Check learner progress survives closing and reopening a disposable database session."""
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from crownpath.db_engine import Base
from crownpath.models import User, LearnerLessonStep, LearnerProgress
from crownpath.main import sync_lesson_progress

def test_progress_roundtrip(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'classroom.db'}")
    try:
        Base.metadata.create_all(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            db.add(User(user_id="student-test", name="Student Test",
                        email="student-test@example.invalid",
                        password_hash="synthetic", role="COSMETOLOGY_PRO",
                        active=True, mfa_enabled=False))
            db.commit()
            item, steps = sync_lesson_progress(db, "student-test", "cosmetology-foundations", 2, now)
            assert item.progress_percent == 0 and steps == []
            db.commit()
        with Session(engine) as db:
            db.add(LearnerLessonStep(step_progress_id="step-one", user_id="student-test",
                       lesson_id="cosmetology-foundations", step_index=1,
                       completed=True, completed_at=now, updated_at=now))
            db.flush()
            item, steps = sync_lesson_progress(db, "student-test", "cosmetology-foundations", 2, now)
            assert steps == [1] and item.progress_percent == 50
            db.commit()
        with Session(engine) as db:
            db.add(LearnerLessonStep(step_progress_id="step-two", user_id="student-test",
                       lesson_id="cosmetology-foundations", step_index=2,
                       completed=True, completed_at=now, updated_at=now))
            db.flush()
            item, steps = sync_lesson_progress(db, "student-test", "cosmetology-foundations", 2, now)
            assert steps == [1, 2] and item.status == "COMPLETED"
            assert item.progress_percent == 100
            db.commit()
        with Session(engine) as db:
            saved = db.query(LearnerProgress).filter_by(
                user_id="student-test", lesson_id="cosmetology-foundations").one()
            assert saved.status == "COMPLETED" and saved.progress_percent == 100
    finally:
        engine.dispose()
