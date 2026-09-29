import ast
from pathlib import Path
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


class MigrationSafetyBaselineTest(unittest.TestCase):
    def test_core_schema_baseline_remains_registered(self):
        self.assertTrue(CORE_TABLES.issubset(set(Base.metadata.tables)))

    def test_database_initialization_does_not_import_curriculum_models(self):
        database_path = Path(__file__).parents[1] / "crownpath" / "database.py"
        tree = ast.parse(database_path.read_text(encoding="utf-8"))
        imported_modules = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)

        self.assertNotIn("crownpath.curriculum_models", imported_modules)


if __name__ == "__main__":
    unittest.main()
