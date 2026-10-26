"""Pure PostgreSQL target guard tests: no database connections."""
import pytest

from crownpath.payment_mfa_pg_isolation_guard import (
    assert_isolated_pg_target, disposable_schema_name,
)


def test_disposable_target_requires_explicit_acknowledgment():
    with pytest.raises(ValueError):
        assert_isolated_pg_target(
            database_name="crownpath_disposable_12345678",
            schema_name="crownpath_test_12345678",
        )
    assert assert_isolated_pg_target(
        database_name="crownpath_disposable_12345678",
        schema_name="crownpath_test_12345678",
        acknowledged=True,
    )


@pytest.mark.parametrize("bad", [
    "public", "crownpath_test_short", "crownpath_test_12345678;DROP SCHEMA public",
    "crownpath_test_12345678.other", "", None,
])
def test_disposable_schema_rejects_unsafe_names(bad):
    with pytest.raises(ValueError):
        disposable_schema_name(bad)


@pytest.mark.parametrize("bad", [
    "postgres", "crownpath", "crownpath_disposable_short",
    "crownpath_disposable_12345678;DROP DATABASE postgres", None,
])
def test_disposable_database_rejects_unsafe_names(bad):
    with pytest.raises(ValueError):
        assert_isolated_pg_target(
            database_name=bad, schema_name="crownpath_test_12345678",
            acknowledged=True,
        )
