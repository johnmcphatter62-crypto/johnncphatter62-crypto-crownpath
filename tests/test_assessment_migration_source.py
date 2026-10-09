"""Source contract for the Chapter 111 Alembic migration."""
import ast
from pathlib import Path

MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "20261009_02_add_assessment_evidence_storage.py"


def test_assessment_migration_links_to_existing_curriculum_revision():
    tree = ast.parse(MIGRATION.read_text(encoding="utf-8"))
    assignments = {
        target.id: node.value.value
        for node in tree.body if isinstance(node, ast.Assign)
        for target in node.targets if isinstance(target, ast.Name)
        if isinstance(node.value, ast.Constant)
    }
    assert assignments["revision"] == "20261009_02"
    assert assignments["down_revision"] == "20260928_01"


def test_assessment_migration_contains_upgrade_and_downgrade():
    source = MIGRATION.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert {"upgrade", "downgrade"} <= functions
    for table in ("practical_assessments", "assessment_evidence_records", "evidence_storage_objects"):
        assert f'"{table}"' in source
    assert "ck_practical_assessment_distinct_reviewer" in source
