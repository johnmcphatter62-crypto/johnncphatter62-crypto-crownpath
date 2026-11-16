"""Pure preflight checklist for isolated PostgreSQL transaction tests.

This never opens a connection. A human/operator must independently verify
the database is disposable, empty, and not used by CrownPath services.
"""
from crownpath.payment_mfa_pg_dsn_guard import validate_disposable_pg_dsn


REQUIRED_ATTESTATIONS = frozenset({
    "dedicated_disposable_instance",
    "no_application_connections",
    "empty_database_verified",
    "least_privilege_test_role",
    "synthetic_data_only",
    "destruction_approved",
})


def verify_pg_test_preflight(*, dsn, schema_name, attestations):
    if not isinstance(attestations, (set, frozenset)):
        raise ValueError("attestations must be an explicit set")
    if attestations != REQUIRED_ATTESTATIONS:
        raise ValueError("all six isolated test attestations required")
    validate_disposable_pg_dsn(
        dsn, schema_name=schema_name, acknowledged=True,
    )
    return True
