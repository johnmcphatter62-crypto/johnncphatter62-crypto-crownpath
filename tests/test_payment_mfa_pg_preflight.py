"""PostgreSQL test preflight is fail-closed and never connects."""
import pytest

from crownpath.payment_mfa_pg_preflight import (
    REQUIRED_ATTESTATIONS, verify_pg_test_preflight,
)

DSN = "postgresql://localhost/crownpath_disposable_12345678"
SCHEMA = "crownpath_test_12345678"


def test_preflight_requires_every_attestation():
    assert verify_pg_test_preflight(
        dsn=DSN, schema_name=SCHEMA,
        attestations=set(REQUIRED_ATTESTATIONS),
    )
    for missing in REQUIRED_ATTESTATIONS:
        with pytest.raises(ValueError):
            verify_pg_test_preflight(
                dsn=DSN, schema_name=SCHEMA,
                attestations=set(REQUIRED_ATTESTATIONS) - {missing},
            )


def test_preflight_rejects_extra_or_unstructured_attestations():
    with pytest.raises(ValueError):
        verify_pg_test_preflight(
            dsn=DSN, schema_name=SCHEMA,
            attestations=set(REQUIRED_ATTESTATIONS) | {"production_ok"},
        )
    with pytest.raises(ValueError):
        verify_pg_test_preflight(
            dsn=DSN, schema_name=SCHEMA,
            attestations=list(REQUIRED_ATTESTATIONS),
        )
