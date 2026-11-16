"""Pure DSN validation tests; no network or database calls."""
import pytest

from crownpath.payment_mfa_pg_dsn_guard import validate_disposable_pg_dsn

DB = "crownpath_disposable_12345678"
SCHEMA = "crownpath_test_12345678"


def test_dedicated_dsn_is_accepted_without_connecting():
    assert validate_disposable_pg_dsn(
        f"postgresql://localhost/{DB}",
        schema_name=SCHEMA, acknowledged=True,
    )


@pytest.mark.parametrize("dsn", [
    "sqlite:///tmp.db",
    "postgresql://localhost/postgres",
    "postgresql://localhost/crownpath_disposable_short",
    f"postgresql://localhost/{DB}?options=-csearch_path%3Dpublic",
    f"postgresql://localhost/{DB}#fragment",
    f"postgresql://localhost/{DB}/other",
    f"postgresql://localhost/{DB}%2Fother",
    "postgresql:///crownpath_disposable_12345678",
    "",
])
def test_invalid_dsn_is_rejected(dsn):
    with pytest.raises(ValueError):
        validate_disposable_pg_dsn(
            dsn, schema_name=SCHEMA, acknowledged=True,
        )


def test_acknowledgment_required():
    with pytest.raises(ValueError):
        validate_disposable_pg_dsn(
            f"postgresql://localhost/{DB}", schema_name=SCHEMA,
        )
