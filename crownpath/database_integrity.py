"""Read-only CrownPath database integrity inspection.

This module never mutates schema or data. It reports only table presence,
Alembic revision state, and aggregate row counts for selected core tables.
"""
from __future__ import annotations

from sqlalchemy import inspect, text

CORE_TABLES = {
    "users",
    "instructor_requests",
    "learner_progress",
    "learner_lesson_steps",
    "auth_tokens",
    "resource_assignments",
    "audit_events",
    "audio_stations",
    "audio_zones",
    "audio_schedules",
    "audio_devices",
    "audio_zone_devices",
}

CURRICULUM_TABLES = {
    "curriculum_programs",
    "curriculum_courses",
    "curriculum_units",
    "curriculum_lessons",
    "curriculum_unit_lessons",
    "curriculum_lesson_versions",
    "curriculum_activities",
    "curriculum_assessments",
}

COUNT_TABLES = (
    "users",
    "instructor_requests",
    "learner_progress",
    "learner_lesson_steps",
    "resource_assignments",
    "audit_events",
)


def inspect_database(engine) -> dict:
    """Inspect schema and aggregate counts using a read-only transaction."""
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            if connection.dialect.name == "postgresql":
                connection.execute(text("SET TRANSACTION READ ONLY"))

            tables = set(inspect(connection).get_table_names())
            counts = {}
            for table_name in COUNT_TABLES:
                if table_name in tables:
                    counts[table_name] = connection.execute(
                        text(f'SELECT COUNT(*) FROM "{table_name}"')
                    ).scalar_one()

            revision = None
            if "alembic_version" in tables:
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                ).scalar_one_or_none()

            return {
                "read_only": True,
                "core_tables_expected": len(CORE_TABLES),
                "core_tables_present": len(CORE_TABLES & tables),
                "core_tables_missing": sorted(CORE_TABLES - tables),
                "curriculum_tables_expected": len(CURRICULUM_TABLES),
                "curriculum_tables_present": len(CURRICULUM_TABLES & tables),
                "curriculum_tables_missing": sorted(CURRICULUM_TABLES - tables),
                "alembic_version": revision,
                "aggregate_counts": counts,
            }
        finally:
            transaction.rollback()


def verification_record(inspection: dict | None = None) -> dict:
    """Build a non-mutating verification record without asserting a pass."""
    inspection = inspection or {}
    missing_core = list(inspection.get("core_tables_missing") or [])
    has_live_inspection = bool(inspection)
    core_complete = (
        has_live_inspection
        and inspection.get("core_tables_present") == inspection.get("core_tables_expected")
        and not missing_core
    )
    return {
        "verification_status": "UNVERIFIED",
        "verified": False,
        "record_integrity_verified": False,
        "migration_authorized": False,
        "activation_authorized": False,
        "inspection_attached": has_live_inspection,
        "read_only_inspection": inspection.get("read_only") is True if has_live_inspection else False,
        "core_schema_complete": core_complete,
        "alembic_version": inspection.get("alembic_version"),
        "aggregate_counts": inspection.get("aggregate_counts", {}),
        "required_evidence": [
            "Read-only inspection of a restored CrownPath database.",
            "Expected core tables present with no unexplained schema loss.",
            "Aggregate record counts reviewed for plausibility.",
            "Backup or PITR source identified and restore procedure documented.",
            "Owner review recorded before any production migration is considered.",
        ],
        "note": "This record does not verify restored record integrity by itself.",
    }


def recovery_evidence_checklist(inspection: dict | None = None) -> dict:
    """Summarize recovery evidence requirements without granting authorization."""
    record = verification_record(inspection)
    checks = [
        {"key": "backup_source", "label": "Backup or PITR source identified", "status": "REQUIRED"},
        {"key": "separate_restore", "label": "Restore performed in a separate database or service", "status": "REQUIRED"},
        {"key": "read_only_inspection", "label": "Read-only restored-database inspection attached", "status": "PRESENT" if record["read_only_inspection"] else "MISSING"},
        {"key": "core_schema", "label": "Expected core schema present", "status": "PRESENT" if record["core_schema_complete"] else "MISSING"},
        {"key": "aggregate_review", "label": "Aggregate record counts reviewed for plausibility", "status": "REQUIRED"},
        {"key": "owner_review", "label": "Owner verification review recorded", "status": "REQUIRED"},
    ]
    return {
        "review_only": True,
        "verification_status": record["verification_status"],
        "migration_authorized": False,
        "activation_authorized": False,
        "checks": checks,
        "required_sequence": [
            "Identify backup or PITR recovery source.",
            "Restore into a separate database or service.",
            "Run the CrownPath read-only integrity inspection.",
            "Review schema and aggregate counts for plausibility.",
            "Record Owner verification decision separately.",
            "Only then consider a separately approved production migration.",
        ],
        "note": "Checklist completion alone does not verify data integrity or authorize migration.",
    }


def migration_authorization_gate(
    verification: dict | None = None,
    owner_authorization: dict | None = None,
) -> dict:
    """Evaluate migration authorization without executing or persisting anything."""
    verification = verification or {}
    owner_authorization = owner_authorization or {}
    recovery_verified = (
        verification.get("verified") is True
        and verification.get("record_integrity_verified") is True
    )
    owner_explicit = (
        owner_authorization.get("approved") is True
        and bool(owner_authorization.get("owner_id"))
        and bool(owner_authorization.get("approved_at"))
    )
    authorized = recovery_verified and owner_explicit
    blockers = []
    if not recovery_verified:
        blockers.append("Restored-database recovery evidence is not verified.")
    if not owner_explicit:
        blockers.append("Explicit Owner migration authorization is not recorded.")
    return {
        "gate": "MIGRATION_AUTHORIZATION",
        "status": "AUTHORIZED" if authorized else "LOCKED",
        "migration_authorized": authorized,
        "migration_executed": False,
        "activation_authorized": False,
        "learner_release_authorized": False,
        "requirements": {
            "recovery_evidence_verified": recovery_verified,
            "explicit_owner_authorization": owner_explicit,
        },
        "blockers": blockers,
        "note": "Authorization does not execute a migration; execution requires a separate controlled operation.",
    }


def recovery_verification_packet(evidence: dict | None = None) -> dict:
    """Build a structured recovery evidence packet without verifying it."""
    evidence = evidence or {}
    requirements = [
        ("backup_source", "Backup or PITR source identification"),
        ("restore_target", "Separate restored database or service identification"),
        ("restore_time", "Restore point or recovery target"),
        ("inspection_result", "Read-only CrownPath integrity inspection result"),
        ("schema_review", "Core schema review"),
        ("aggregate_review", "Aggregate record-count plausibility review"),
        ("restore_procedure", "Documented restore procedure"),
        ("owner_review", "Owner verification review"),
    ]
    items = []
    for key, label in requirements:
        supplied = evidence.get(key) not in (None, "", [], {})
        items.append({"key": key, "label": label, "evidence_supplied": supplied})
    complete = all(item["evidence_supplied"] for item in items)
    return {
        "packet_type": "RECOVERY_VERIFICATION",
        "status": "EVIDENCE_COMPLETE_UNVERIFIED" if complete else "INCOMPLETE",
        "evidence_complete": complete,
        "verified": False,
        "record_integrity_verified": False,
        "migration_authorized": False,
        "migration_executed": False,
        "activation_authorized": False,
        "learner_release_authorized": False,
        "items": items,
        "note": "Evidence completeness is not verification. A separate Owner verification decision is required.",
    }
