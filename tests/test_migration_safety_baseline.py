import unittest

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


class MigrationSafetyBaselineTest(unittest.TestCase):
    def test_core_schema_baseline_is_explicit(self):
        self.assertEqual(set(Base.metadata.tables), CORE_TABLES)

    def test_curriculum_tables_are_not_registered_by_core_models_import(self):
        self.assertTrue(CURRICULUM_TABLES.isdisjoint(Base.metadata.tables))


if __name__ == "__main__":
    unittest.main()
