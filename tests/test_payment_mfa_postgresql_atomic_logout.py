"""PostgreSQL atomic logout integration test: deliberately blocked.

No PostgreSQL connection or schema change is permitted until an isolated,
non-destructive test environment is provisioned and reviewed. CI reports skip.
"""
import pytest


@pytest.mark.skip(reason="PostgreSQL integration blocked pending verified disposable schema isolation")
def test_postgres_atomic_logout_rollback():
    """Placeholder only: does not exercise PostgreSQL transaction semantics."""
    raise AssertionError("Blocked PostgreSQL test must never execute")
