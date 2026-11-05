"""Additional pure guardrail for PostgreSQL test connection configuration.

Does not connect, inspect, migrate or mutate any database. Names and DSN
properties are necessary but insufficient to establish isolation.
"""
from urllib.parse import urlsplit

from crownpath.payment_mfa_pg_isolation_guard import assert_isolated_pg_target


def validate_disposable_pg_dsn(url, *, schema_name, acknowledged=False):
    if not isinstance(url, str) or not url:
        raise ValueError("explicit disposable PostgreSQL DSN required")
    parsed = urlsplit(url)
    if parsed.scheme not in ("postgresql", "postgresql+psycopg", "postgresql+psycopg2"):
        raise ValueError("PostgreSQL DSN required")
    if not parsed.hostname or not parsed.path.startswith("/") or parsed.query or parsed.fragment:
        raise ValueError("host, dedicated database and no DSN query/fragment required")
    database_name = parsed.path[1:]
    if "/" in database_name or "%" in database_name:
        raise ValueError("ambiguous database name")
    assert_isolated_pg_target(
        database_name=database_name,
        schema_name=schema_name,
        acknowledged=acknowledged,
    )
    return True
