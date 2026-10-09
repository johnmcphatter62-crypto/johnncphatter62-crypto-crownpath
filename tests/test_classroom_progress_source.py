"""Regression checks for the learner lesson progress indicator.

These source-contract tests do not replace browser or accessibility testing.
"""
from pathlib import Path


APP_JS = Path(__file__).resolve().parents[1] / "frontend" / "app.js"


def test_progress_indicator_uses_native_element_and_accessible_name():
    source = APP_JS.read_text(encoding="utf-8")
    assert "function createLessonProgress(item)" in source
    assert "document.createElement('progress')" in source
    assert "progress.setAttribute('aria-label'" in source
    assert "Lesson steps completed:" in source


def test_progress_indicator_bounds_and_dashboard_integration():
    source = APP_JS.read_text(encoding="utf-8")
    assert "Math.min(100,Math.max(0,Number(item.progress)||0))" in source
    assert "wrap.append(createLessonProgress(item))" in source
    assert "function lessonItem(item)" in source
