import importlib.util
from pathlib import Path
import unittest

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

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


def load_migration():
    path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20260928_01_add_curriculum_structure.py"
    )
    spec = importlib.util.spec_from_file_location("crownpath_curriculum_migration", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CurriculumMigrationRoundTripTest(unittest.TestCase):
    def setUp(self):
        self.engine = sa.create_engine("sqlite:///:memory:")
        core_metadata = sa.MetaData()
        for table_name in CORE_TABLES:
            Base.metadata.tables[table_name].to_metadata(core_metadata)
        core_metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def run_migration_function(self, function):
        migration = load_migration()
        with self.engine.begin() as connection:
            context = MigrationContext.configure(connection)
            operations = Operations(context)
            original_op = migration.op
            migration.op = operations
            try:
                function(migration)
            finally:
                migration.op = original_op

    def test_upgrade_creates_only_curriculum_tables_alongside_core(self):
        self.run_migration_function(lambda migration: migration.upgrade())
        tables = set(sa.inspect(self.engine).get_table_names())

        self.assertTrue(CORE_TABLES.issubset(tables))
        self.assertTrue(CURRICULUM_TABLES.issubset(tables))
        self.assertEqual(tables, CORE_TABLES | CURRICULUM_TABLES)

    def test_downgrade_removes_curriculum_and_preserves_core(self):
        self.run_migration_function(lambda migration: migration.upgrade())
        self.run_migration_function(lambda migration: migration.downgrade())
        tables = set(sa.inspect(self.engine).get_table_names())

        self.assertEqual(tables, CORE_TABLES)
        self.assertTrue(CURRICULUM_TABLES.isdisjoint(tables))


if __name__ == "__main__":
    unittest.main()
