"""Guardrail for future isolated PostgreSQL integration test setup.

Pure validation only: never opens a connection or creates a schema.
"""
import re


def disposable_schema_name(value):
    """Accept only explicitly named disposable schemas with safe SQL identifiers."""
    if not isinstance(value, str):
        raise ValueError("schema name required")
    if not re.fullmatch(r"crownpath_test_[a-z0-9_]{8,48}", value):
        raise ValueError("dedicated crownpath_test_ schema required")
    return value


def assert_isolated_pg_target(*, database_name, schema_name, acknowledged=False):
    """Fail closed without touching a database.

    Name checks and acknowledgment alone DO NOT prove isolation; a future
    runner must additionally verify DB identity, role privileges and emptiness.
    """
    if acknowledged is not True:
        raise ValueError("explicit disposable test acknowledgment required")
    if not isinstance(database_name, str) or not re.fullmatch(
        r"crownpath_disposable_[a-z0-9_]{8,48}", database_name
    ):
        raise ValueError("dedicated disposable database name required")
    disposable_schema_name(schema_name)
    return True
