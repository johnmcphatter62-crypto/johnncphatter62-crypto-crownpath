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

    command.upgrade(_alembic_config(), "head")

    upgraded = set(sa.inspect(engine).get_table_names())
    assert CORE_TABLES.issubset(upgraded)
    assert CURRICULUM_TABLES.issubset(upgraded)
    assert "alembic_version" in upgraded
    assert upgraded == CORE_TABLES | CURRICULUM_TABLES | {"alembic_version"}

    with engine.connect() as connection:
        revision = connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
    assert revision == "20260928_01"

    command.downgrade(_alembic_config(), "20260928_00")

    downgraded = set(sa.inspect(engine).get_table_names())
    assert CORE_TABLES.issubset(downgraded)
    assert CURRICULUM_TABLES.isdisjoint(downgraded)
    assert downgraded == CORE_TABLES | {"alembic_version"}

    with engine.connect() as connection:
        revision = connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
    assert revision == "20260928_00"
