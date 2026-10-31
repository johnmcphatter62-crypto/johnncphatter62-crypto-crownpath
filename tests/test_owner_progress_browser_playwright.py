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
            page.evaluate("""() => { window.jsonRequest = async path => {
                if (path !== "/api/owner/learner-progress") throw Error("Unexpected endpoint");
                return {learners: [{name: "Synthetic Student", role: "COSMETOLOGY_PRO",
                    lessons_completed: 2, lessons_total: 4, overall_progress: 50}]};
            }; }""")
            page.evaluate("() => { " + handler + "; return loadOwnerLearnerProgress(); }")
            assert page.locator("#ownerLearnerProgressList .session-card").count() == 1
            assert "2 of 4 lessons complete" in page.locator("#ownerLearnerProgressList").inner_text()
            assert "1 learner(s) loaded." in page.locator("#learnerProgressMessage").inner_text()
        finally:
            browser.close()


def test_public_homepage_keeps_owner_private_and_shows_classroom_entry():
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    html = (Path(__file__).resolve().parents[1] / "frontend" / "index.html").read_text(encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(html)
            assert page.get_by_role("heading", name="Sign in to CrownPath").is_visible()
            assert page.locator("#loginForm").is_visible()
            assert page.locator("#ownerPanel").is_hidden()
            assert page.locator("#learnerDashboard").is_hidden()
            assert page.locator("#loginEmail").get_attribute("type") == "email"
            assert page.locator("#loginPassword").get_attribute("type") == "password"
        finally:
            browser.close()


def test_browser_student_progress_rejects_html_injection():
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
            page.evaluate("""() => { window.jsonRequest = async () => ({
                learners: [{name: "<img src=x onerror=alert(1)>",
                    role: "COSMETOLOGY_PRO", lessons_completed: 0,
                    lessons_total: 4, overall_progress: 0}]
            }); }""")
            page.evaluate("() => { " + handler + "; return loadOwnerLearnerProgress(); }")
            assert page.locator("#ownerLearnerProgressList img").count() == 0
            assert "<img src=x onerror=alert(1)>" in page.locator("#ownerLearnerProgressList").inner_text()
        finally:
            browser.close()


def test_browser_progress_refresh_clears_stale_learner_cards():
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
            page.evaluate("""() => {
                window.reportLearners = [{name: "Synthetic Learner", role: "BARBER",
                    lessons_completed: 1, lessons_total: 3, overall_progress: 33}];
                window.jsonRequest = async () => ({learners: window.reportLearners});
            }""")
            page.evaluate("() => { " + handler + "; return loadOwnerLearnerProgress(); }")
            assert page.locator("#ownerLearnerProgressList .session-card").count() == 1
            page.evaluate("() => { window.reportLearners = []; }")
            page.evaluate("() => { " + handler + "; return loadOwnerLearnerProgress(); }")
            assert page.locator("#ownerLearnerProgressList .session-card").count() == 0
            assert page.locator("#learnerProgressMessage").inner_text() == "No learners to report yet."
        finally:
            browser.close()


def test_browser_student_and_owner_dashboard_visibility_by_role():
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright
    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    js = (root / "frontend" / "app.js").read_text(encoding="utf-8")
    start = js.index("function showSession(user)")
    end = js.index("function clearSession()", start)
    handler = js[start:end]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(html)
            page.evaluate("""() => {
                window.resetMfaLogin = () => {};
                window.hideRecoveryCodes = () => {};
                window.loadLearnerDashboard = () => {};
                window.loadMyInstructorRequests = () => {};
                window.loadOwnerUsers = () => {};
                window.loadInstructorRequests = () => {};
                window.loadOwnerLearnerProgress = () => {};
                window.loadOwnerCurriculum = () => {};
                window.sessionCard = document.querySelector("#sessionCard");
                window.ownerPanel = document.querySelector("#ownerPanel");
                window.ownerActivation = document.querySelector("#ownerActivation");
                window.learnerDashboard = document.querySelector("#learnerDashboard");
                window.instructorRequestPanel = document.querySelector("#instructorRequestPanel");
                window.mfaSetupButton = document.querySelector("#mfaSetupButton");
                window.mfaSetupPanel = document.querySelector("#mfaSetupPanel");
                window.mfaSetupMessage = document.querySelector("#mfaSetupMessage");
            }""")
            page.evaluate("() => { " + handler + "; showSession({name: 'Synthetic Learner', role: 'COSMETOLOGY_PRO', mfa_enabled: false}); }")
            assert page.locator("#learnerDashboard").is_visible()
            assert page.locator("#ownerPanel").is_hidden()
            page.evaluate("() => { " + handler + "; showSession({name: 'Synthetic Owner', role: 'OWNER', mfa_enabled: true}); }")
            assert page.locator("#ownerPanel").is_visible()
            assert page.locator("#learnerDashboard").is_hidden()
        finally:
            browser.close()
