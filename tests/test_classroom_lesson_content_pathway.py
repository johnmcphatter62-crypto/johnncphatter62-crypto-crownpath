"""Verify a learner pathway resolves usable lesson content without live services."""
from crownpath.main import learner_catalog, lesson_for_role
from fastapi import HTTPException


def test_cosmetology_classroom_content_is_available():
    catalog = learner_catalog("COSMETOLOGY_PRO")
    assert catalog
    lesson_id, title = catalog[0]
    resolved_title, content = lesson_for_role("COSMETOLOGY_PRO", lesson_id)
    assert resolved_title == title
    assert isinstance(content, dict)
    assert isinstance(content.get("steps"), list)
    assert len(content["steps"]) > 0


def test_learner_cannot_open_another_pathways_lesson():
    try:
        lesson_for_role("HOME_CARE", "cosmetology-foundations")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("Cross-pathway lesson was unexpectedly accessible")
