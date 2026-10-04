from pathlib import Path

HTML = Path("frontend/index.html").read_text(encoding="utf-8")
APP = Path("frontend/app.js").read_text(encoding="utf-8")


def test_owner_hierarchy_forms_are_present():
    for form_id in ("curriculumCourseForm","curriculumUnitForm","curriculumLessonForm","curriculumVersionForm"):
        assert f'id="{form_id}"' in HTML


def test_owner_hierarchy_uses_owner_api_only():
    for path in (
        "/api/owner/curriculum/courses",
        "/api/owner/curriculum/units",
        "/api/owner/curriculum/lessons",
        "/api/owner/curriculum/lesson-versions",
    ):
        assert path in APP


def test_lesson_version_json_is_validated_before_submission():
    assert "JSON.parse(raw)" in APP
    assert "Lesson content must be valid JSON." in APP


def test_workspace_has_no_publish_or_release_action():
    combined=(HTML+"\n"+APP).lower()
    assert 'publish curriculum' not in combined
    assert '/publish' not in combined
    assert '/release' not in combined


def test_locked_condition_detection_not_added():
    assert "condition detection" not in (HTML+"\n"+APP).lower()
