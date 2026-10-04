import ast
from pathlib import Path

import sqlalchemy as sa

from crownpath.database_integrity import (
    CORE_TABLES,
    CURRICULUM_TABLES,
    inspect_database,
)


def test_integrity_checker_reports_schema_without_mutation():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    metadata = sa.MetaData()
    for table_name in sorted(CORE_TABLES):
        sa.Table(table_name, metadata, sa.Column("id", sa.Integer, primary_key=True))
    metadata.create_all(engine)

    result = inspect_database(engine)

    assert result["read_only"] is True
    assert result["core_tables_present"] == len(CORE_TABLES)
    assert result["core_tables_missing"] == []
    assert result["curriculum_tables_present"] == 0
    assert set(result["curriculum_tables_missing"]) == CURRICULUM_TABLES
    assert result["alembic_version"] is None


def test_integrity_checker_source_contains_no_data_or_schema_mutation():
    source = Path("crownpath/database_integrity.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"}

    string_values = [
        node.value.upper()
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]

    for value in string_values:
        for keyword in forbidden:
            assert not value.lstrip().startswith(keyword + " ")


def test_integrity_checker_does_not_emit_sensitive_columns():
    source = Path("crownpath/database_integrity.py").read_text(encoding="utf-8").lower()
    assert "password_hash" not in source
    assert "mfa_secret" not in source
    assert "email" not in source
    assert "database_url" not in source
