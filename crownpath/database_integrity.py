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
