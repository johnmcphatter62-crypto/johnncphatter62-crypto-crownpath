"""HTTP smoke test for the combined CrownPath homepage and Owner interface."""
from fastapi.testclient import TestClient
import crownpath.main as main


def test_homepage_serves_owner_classroom_and_student_progress_assets():
    with TestClient(main.app) as client:
        page = client.get("/")
        assert page.status_code == 200, page.text
        assert "Owner Management Dashboard" in page.text
        assert 'id="ownerPanel"' in page.text
        assert 'id="learnerDashboard"' in page.text
        assert 'id="refreshLearnerProgress"' in page.text
        script = client.get("/static/app.js")
        assert script.status_code == 200, script.text
        assert "loadOwnerLearnerProgress()" in script.text
        assert "/api/owner/learner-progress" in script.text


def test_homepage_serves_frontend_with_safe_default_visibility():
    with TestClient(main.app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert '<section id="ownerPanel" class="access" hidden>' in page.text
        assert '<section id="learnerDashboard"' in page.text
        assert 'id="refreshLearnerProgress"' in page.text
