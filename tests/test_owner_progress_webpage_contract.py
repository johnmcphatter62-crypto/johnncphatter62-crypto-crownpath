"""Static contract checks for Owner student progress webpage wiring."""
from pathlib import Path


def test_owner_progress_webpage_elements_and_fetch_wiring():
    root = Path(__file__).resolve().parents[1]
    html = (root / "frontend" / "index.html").read_text(encoding="utf-8")
    script = (root / "frontend" / "app.js").read_text(encoding="utf-8")
    assert 'id="ownerLearnerProgressList"' in html
    assert 'id="learnerProgressMessage"' in html
    assert 'id="refreshLearnerProgress"' in html
    assert "async function loadOwnerLearnerProgress()" in script
    assert "jsonRequest('/api/owner/learner-progress')" in script
    assert "addEventListener('click',loadOwnerLearnerProgress)" in script
    assert "loadOwnerLearnerProgress();loadOwnerCurriculum()" in script
    assert "heading.textContent=learner.name" in script
    assert "summary.textContent=learner.lessons_completed" in script

def test_owner_progress_page_escapes_student_names():
    root = Path(__file__).resolve().parents[1]
    script = (root / "frontend" / "app.js").read_text(encoding="utf-8")
    start = script.index("async function loadOwnerLearnerProgress()")
    end = script.index("async function loadInstructorRequests()", start)
    handler = script[start:end]
    assert "heading.textContent=learner.name" in handler
    assert "summary.textContent=learner.lessons_completed" in handler
    assert "list.append(card)" in handler
    assert "innerHTML=learner." not in handler
    assert "eval(" not in handler
