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
