from pathlib import Path

MAIN = Path("crownpath/main.py").read_text(encoding="utf-8")
SERVICE = Path("crownpath/owner_curriculum.py").read_text(encoding="utf-8")


def test_owner_draft_hierarchy_routes_exist():
    for path in (
        '/api/owner/curriculum/courses',
        '/api/owner/curriculum/units',
        '/api/owner/curriculum/lessons',
        '/api/owner/curriculum/lesson-versions',
    ):
        assert path in MAIN


def test_owner_hierarchy_routes_require_academy_manage():
    lines = [
        line for line in MAIN.splitlines()
        if line.startswith("def owner_curriculum_create_")
    ]
    assert lines
    assert all('Depends(require_permission("academy.manage"))' in line for line in lines)


def test_structure_includes_draft_hierarchy():
    assert '"units": [unit_dict(item) for item in units]' in SERVICE
    assert '"lessons": [lesson_dict(item) for item in lessons]' in SERVICE


def test_no_publish_or_release_route_added():
    route_lines = [
        line.lower() for line in MAIN.splitlines()
        if line.startswith("@app.") and "/api/owner/curriculum" in line
    ]
    assert route_lines
    assert all("publish" not in line and "release" not in line for line in route_lines)


def test_locked_condition_detection_not_added():
    combined = (MAIN + "\n" + SERVICE).lower()
    assert "condition detection" not in combined
