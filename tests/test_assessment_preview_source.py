"""Regression checks for the protected, read-only assessment preview route."""
from pathlib import Path


def test_preview_route_is_explicitly_non_persistent():
    source = (Path(__file__).resolve().parents[1] / "crownpath" / "main.py").read_text()
    start = source.index('@app.post("/api/instructor/learners/{learner_id}/assessments/preview")')
    end = source.index('@app.get("/api/academy")', start)
    route = source[start:end]
    assert "Depends(current_user)" in route
    assert "can_review_assigned_learner(user,learner_id)" in route
    assert "get_user_by_id(learner_id)" in route
    assert '"preview_only":True' in route
    assert '"approval_recorded":False' in route
    assert "stage_assessment_review" not in route
    assert "db.commit()" not in route
