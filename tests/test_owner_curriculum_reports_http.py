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
            db.add(User(user_id="student-test", name="Synthetic Student",
                        email="student-report@example.com",
                        password_hash=auth.hash_password("SyntheticPassword!2026"),
                        role="COSMETOLOGY_PRO", active=True, mfa_enabled=False))
            db.commit()
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={
                "email": "owner-reports@example.com",
                "password": "SyntheticPassword!2026"})
            assert login.status_code == 200, login.text
            # A separate authenticated learner must not access Owner reports.
            with TestClient(main.app, headers={"Origin": "http://testserver"}) as learner_client:
                learner_login = learner_client.post("/api/auth/login", json={
                    "email": "student-report@example.com",
                    "password": "SyntheticPassword!2026"})
                assert learner_login.status_code == 200, learner_login.text
                learner_me = learner_client.get("/api/auth/me")
                assert learner_me.status_code == 200, learner_me.text
                assert learner_me.json()["role"] == "COSMETOLOGY_PRO"
                # Student cannot read other Owner-only curriculum summaries.
                for protected_path in (
                    "/api/owner/curriculum/progress-summary",
                    "/api/owner/curriculum/completion-dashboard",
                ):
                    protected = learner_client.get(protected_path)
                    assert protected.status_code in (401, 403), (protected_path, protected.text)
                # Learner may read their own classroom dashboard, not Owner data.
                dashboard = learner_client.get("/api/learner/dashboard")
                assert dashboard.status_code == 200, dashboard.text
                assert isinstance(dashboard.json()["modules"], list)
                assert "overall_progress" in dashboard.json()
                # A learner may open a curriculum lesson in their own session.
                opened = learner_client.post("/api/learner/lessons/cosmetology-foundations/open")
                assert opened.status_code == 200, opened.text
                assert opened.json()["lesson"]["lesson_id"] == "cosmetology-foundations"
                # Completing one real lesson step updates the learner progress API.
                first_step = learner_client.post(
                    "/api/learner/lessons/cosmetology-foundations/steps/1/complete")
                assert first_step.status_code == 200, first_step.text
                step_lesson = first_step.json()["lesson"]
                assert 1 in step_lesson["completed_steps"]
                assert step_lesson["progress"] > 0
                # Completing the same step again must be idempotent.
                repeated_step = learner_client.post(
                    "/api/learner/lessons/cosmetology-foundations/steps/1/complete")
                assert repeated_step.status_code == 200, repeated_step.text
                assert repeated_step.json()["lesson"]["completed_steps"] == step_lesson["completed_steps"]
                assert repeated_step.json()["lesson"]["progress"] == step_lesson["progress"]
                # The classroom dashboard must reflect saved step progress.
                updated_dashboard = learner_client.get("/api/learner/dashboard")
                assert updated_dashboard.status_code == 200, updated_dashboard.text
                assert updated_dashboard.json()["overall_progress"] > dashboard.json()["overall_progress"]
                # Reject nonexistent lesson steps without changing saved progress.
                invalid_step = learner_client.post(
                    "/api/learner/lessons/cosmetology-foundations/steps/999/complete")
                assert invalid_step.status_code == 404, invalid_step.text
                unchanged_dashboard = learner_client.get("/api/learner/dashboard")
                assert unchanged_dashboard.status_code == 200, unchanged_dashboard.text
                assert unchanged_dashboard.json()["overall_progress"] == updated_dashboard.json()["overall_progress"]
                private_report = learner_client.get("/api/owner/learner-progress")
                assert private_report.status_code in (401, 403), private_report.text
            # Owner access remains available after the separate learner login.
            owner_me = client.get("/api/auth/me")
            assert owner_me.status_code == 200, owner_me.text
            assert owner_me.json()["role"] == "OWNER"
            learner_report = client.get("/api/owner/learner-progress")
            assert learner_report.status_code == 200, learner_report.text
            assert learner_report.json()["read_only"] is True
            learners = learner_report.json()["learners"]
            assert len(learners) == 1
            assert learners[0]["user_id"] == "student-test"
            assert learners[0]["role"] == "COSMETOLOGY_PRO"
            assert learners[0]["lessons_completed"] == 0
            assert 0 < learners[0]["overall_progress"] < 100
            assert learners[0]["lessons_total"] > 0
            assert all(lesson["status"] in ("NOT_STARTED", "IN_PROGRESS") for lesson in learners[0]["lessons"])
            assert any(lesson["status"] == "IN_PROGRESS" for lesson in learners[0]["lessons"])
            # Finish the lesson through the real student API after checking partial progress.
            with TestClient(main.app, headers={"Origin": "http://testserver"}) as completing_learner:
                login_again = completing_learner.post("/api/auth/login", json={
                    "email": "student-report@example.com",
                    "password": "SyntheticPassword!2026"})
                assert login_again.status_code == 200, login_again.text
                # Progress saved in the first login must survive a fresh session.
                resumed_dashboard = completing_learner.get("/api/learner/dashboard")
                assert resumed_dashboard.status_code == 200, resumed_dashboard.text
                assert (
                    resumed_dashboard.json()["overall_progress"]
                    == updated_dashboard.json()["overall_progress"]
                )
                # The Owner-only report must remain inaccessible after a fresh learner login.
                resumed_owner_report = completing_learner.get("/api/owner/learner-progress")
                assert resumed_owner_report.status_code in (401, 403), resumed_owner_report.text
                total_steps = opened.json()["lesson"]["total_steps"]
                assert total_steps >= 1
                for step_index in range(2, total_steps + 1):
                    step_result = completing_learner.post(
                        f"/api/learner/lessons/cosmetology-foundations/steps/{step_index}/complete")
                    assert step_result.status_code == 200, step_result.text
                # A repeat completion request must not add extra completed steps.
                repeat_last = completing_learner.post(
                    f"/api/learner/lessons/cosmetology-foundations/steps/{total_steps}/complete")
                assert repeat_last.status_code == 200, repeat_last.text
                assert repeat_last.json()["lesson"]["status"] == "COMPLETED"
                assert repeat_last.json()["lesson"]["progress"] == 100
                assert repeat_last.json()["lesson"]["completed_step_count"] == total_steps
                # Completing the entire lesson again must remain idempotent.
                repeat_lesson = completing_learner.post(
                    "/api/learner/lessons/cosmetology-foundations/complete")
                assert repeat_lesson.status_code == 200, repeat_lesson.text
                assert repeat_lesson.json()["lesson"]["status"] == "COMPLETED"
                assert repeat_lesson.json()["lesson"]["progress"] == 100
                # A completed lesson must reject nonexistent steps without losing completion.
                invalid_after_completion = completing_learner.post(
                    "/api/learner/lessons/cosmetology-foundations/steps/999/complete")
                assert invalid_after_completion.status_code == 404, invalid_after_completion.text
                # The learner dashboard must retain the completed lesson across requests.
                completion_dashboard = completing_learner.get("/api/learner/dashboard")
                assert completion_dashboard.status_code == 200, completion_dashboard.text
                assert completion_dashboard.json()["overall_progress"] > updated_dashboard.json()["overall_progress"]
                # A learner must still be denied the Owner report after completing a lesson.
                denied_after_completion = completing_learner.get("/api/owner/learner-progress")
                assert denied_after_completion.status_code in (401, 403), denied_after_completion.text
                # Completing a lesson must not unlock the Owner curriculum dashboards.
                for owner_endpoint in (
                    "/api/owner/curriculum/progress-summary",
                    "/api/owner/curriculum/completion-dashboard",
                ):
                    denied = completing_learner.get(owner_endpoint)
                    assert denied.status_code in (401, 403), denied.text
                finished = completing_learner.get("/api/learner/dashboard")
                assert finished.status_code == 200, finished.text
                assert finished.json()["overall_progress"] >= updated_dashboard.json()["overall_progress"]
            updated_report = client.get("/api/owner/learner-progress")
            assert updated_report.status_code == 200, updated_report.text
            updated = updated_report.json()["learners"][0]
            assert updated["lessons_completed"] == 1
            assert updated["overall_progress"] > 0
            assert updated["lessons"][0]["status"] == "COMPLETED"
            assert updated["lessons"][0]["progress"] == 100
            assert updated_report.json()["read_only"] is True
            assert updated["lessons_total"] == learners[0]["lessons_total"]
            assert updated["overall_progress"] <= 100
            assert sum(item["status"] == "COMPLETED" for item in updated["lessons"]) == 1
            assert all(item["progress"] in (0, 100) for item in updated["lessons"])
            # Repeated completion requests must not inflate the Owner's totals.
            assert updated["lessons_completed"] <= updated["lessons_total"]
            assert updated["lessons_completed"] == sum(
                lesson["status"] == "COMPLETED" for lesson in updated["lessons"]
            )
            assert updated["overall_progress"] > learners[0]["overall_progress"]
            # The Owner's report must be stable across consecutive read-only requests.
            repeat_report = client.get("/api/owner/learner-progress")
            assert repeat_report.status_code == 200, repeat_report.text
            assert repeat_report.json() == updated_report.json()
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
