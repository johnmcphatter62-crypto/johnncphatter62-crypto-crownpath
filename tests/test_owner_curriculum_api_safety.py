import ast
from pathlib import Path


MAIN_PATH = Path("crownpath/main.py")


def _main_source():
    return MAIN_PATH.read_text(encoding="utf-8")


def test_curriculum_models_are_not_top_level_imported_before_init_db():
    tree = ast.parse(_main_source())
    top_level_imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level_imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            top_level_imports.append(node.module or "")
    assert "crownpath.curriculum_models" not in top_level_imports
    assert "crownpath.owner_curriculum" not in top_level_imports


def test_owner_curriculum_api_requires_owner_academy_manage_permission():
    source = _main_source()
    routes = (
        "owner_curriculum_structure",
        "owner_curriculum_create_program",
        "owner_curriculum_review_versions",
        "owner_curriculum_approve_version",
    )
    for route in routes:
        start = source.index(f"def {route}")
        body = source[start:start + 1200]
        assert 'Depends(require_permission("academy.manage"))' in body


def test_owner_curriculum_api_uses_lazy_service_imports():
    source = _main_source()
    assert source.count("from crownpath import owner_curriculum") >= 4


def test_owner_curriculum_api_has_no_publish_or_release_route():
    source = _main_source().lower()
    owner_route_lines = [
        line for line in source.splitlines()
        if line.startswith('@app.') and "/api/owner/curriculum" in line
    ]
    assert owner_route_lines
    assert all("publish" not in line and "release" not in line for line in owner_route_lines)
