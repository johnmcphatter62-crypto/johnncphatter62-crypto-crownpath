"""Optional Chromium smoke test using synthetic Owner progress data."""
from pathlib import Path
import pytest


def test_owner_report_renders_in_chromium():
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    js = (root / "frontend" / "app.js").read_text(encoding="utf-8")
    start = js.index("async function loadOwnerLearnerProgress()")
    end = js.index("async function loadInstructorRequests()", start)
    handler = js[start:end]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(html)
            assert page.locator("#ownerPanel").is_hidden()
            page.evaluate("""window.jsonRequest = async path => {
                if (path !== "/api/owner/learner-progress") throw Error("Unexpected endpoint");
                return {learners: [{name: "Synthetic Student", role: "COSMETOLOGY_PRO",
                    lessons_completed: 2, lessons_total: 4, overall_progress: 50}]};
            };""")
            page.evaluate("() => { " + handler + "; return loadOwnerLearnerProgress(); }")
            assert page.locator("#ownerLearnerProgressList .session-card").count() == 1
            assert "2 of 4 lessons complete" in page.locator("#ownerLearnerProgressList").inner_text()
            assert "1 learner(s) loaded." in page.locator("#learnerProgressMessage").inner_text()
        finally:
            browser.close()
