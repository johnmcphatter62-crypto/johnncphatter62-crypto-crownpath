import os
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

import crownpath.models  # noqa: F401
from crownpath.db_engine import Base


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

SCHOOL_TABLES = {"schools", "school_memberships", "school_owner_authorizations"}


def _ci_database_url():
    url = os.environ.get("CROWNPATH_DATABASE_URL", "")
    if "localhost:5432/crownpath_ci" not in url:
        pytest.skip("PostgreSQL migration integration test is restricted to the disposable CI database.")
    return url


@pytest.fixture()
def postgres_core_schema():
    engine = sa.create_engine(_ci_database_url())
    metadata = sa.MetaData()
    for table_name in CORE_TABLES:
        Base.metadata.tables[table_name].to_metadata(metadata)

    with engine.begin() as connection:
        inspector = sa.inspect(connection)
        existing = inspector.get_table_names()
        for table_name in existing:
            connection.execute(sa.text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
        metadata.create_all(connection)

    yield engine

    with engine.begin() as connection:
        for table_name in sa.inspect(connection).get_table_names():
            connection.execute(sa.text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
    engine.dispose()


def _alembic_config():
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    return config


def test_existing_core_schema_without_history_upgrades_and_downgrades(postgres_core_schema):
    engine = postgres_core_schema
    before = set(sa.inspect(engine).get_table_names())
    assert before == CORE_TABLES
    assert "alembic_version" not in before

    # Preserve a synthetic existing learner through both migration directions.
    with engine.begin() as connection:
        connection.execute(sa.text(
            "INSERT INTO users (user_id, name, email, password_hash, role, active, "
            "email_verified, mfa_enabled, failed_login_attempts, created_at) "
            "VALUES (:user_id, :name, :email, :password_hash, :role, "
            ":active, :email_verified, :mfa_enabled, :failed_login_attempts, :created_at)"
        ), {
            "user_id": "CP-USR-MIGRATION-TEST",
            "name": "Migration Learner",
            "email": "migration-learner@example.invalid",
            "password_hash": "synthetic-not-a-password",
            "role": "BARBER",
            "active": True,
            "email_verified": False,
            "mfa_enabled": False,
            "failed_login_attempts": 0,
            "created_at": "2026-11-04 00:00:00",
        })

    command.upgrade(_alembic_config(), "head")

    upgraded = set(sa.inspect(engine).get_table_names())
    assert CORE_TABLES.issubset(upgraded)
    assert CURRICULUM_TABLES.issubset(upgraded)
    assert SCHOOL_TABLES.issubset(upgraded)
    assert "alembic_version" in upgraded
    assert upgraded == CORE_TABLES | CURRICULUM_TABLES | SCHOOL_TABLES | {"alembic_version"}

    # Newly migrated school Owner grants are empty and fail closed by default.
    with engine.connect() as connection:
        grants = connection.scalar(sa.text(
            "SELECT COUNT(*) FROM school_owner_authorizations"
        ))
        assert grants == 0
        grant_columns = {
            column["name"]: column
            for column in sa.inspect(connection).get_columns("school_owner_authorizations")
        }
        assert grant_columns["school_id"]["nullable"] is False
        assert grant_columns["owner_user_id"]["nullable"] is False
        assert grant_columns["active"]["nullable"] is False
        assert grant_columns["revoked_at"]["nullable"] is True
        assert grant_columns["expires_at"]["nullable"] is True
        unique_constraints = sa.inspect(connection).get_unique_constraints(
            "school_owner_authorizations"
        )
        assert any(
            set(item["column_names"]) == {"school_id", "owner_user_id"}
            for item in unique_constraints
        )

    with engine.connect() as connection:
        revision = connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
    assert revision == "20261104_03"
    with engine.connect() as connection:
        learner = connection.execute(sa.text(
            "SELECT email, role, active FROM users WHERE user_id = :user_id"
        ), {"user_id": "CP-USR-MIGRATION-TEST"}).one()
    assert learner.email == "migration-learner@example.invalid"
    assert learner.role == "BARBER"
    assert learner.active is True

    command.downgrade(_alembic_config(), "20260928_00")

    downgraded = set(sa.inspect(engine).get_table_names())
    assert CORE_TABLES.issubset(downgraded)
    assert CURRICULUM_TABLES.isdisjoint(downgraded)
    assert SCHOOL_TABLES.isdisjoint(downgraded)
    assert downgraded == CORE_TABLES | {"alembic_version"}

    with engine.connect() as connection:
        revision = connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
    assert revision == "20260928_00"
    with engine.connect() as connection:
        learner = connection.execute(sa.text(
            "SELECT email, role, active FROM users WHERE user_id = :user_id"
        ), {"user_id": "CP-USR-MIGRATION-TEST"}).one()
    assert learner.email == "migration-learner@example.invalid"
    assert learner.role == "BARBER"
    assert learner.active is True
