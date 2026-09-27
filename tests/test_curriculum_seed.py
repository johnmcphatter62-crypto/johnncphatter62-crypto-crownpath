import os
import unittest
import uuid

os.environ.setdefault("CROWNPATH_ENV", "staging")
os.environ.setdefault("CROWNPATH_SECRET_KEY", "ci-only-secret-key-for-curriculum-tests-123456789")

from sqlalchemy import delete, select

from crownpath.curriculum_models import CurriculumCourse, CurriculumLesson, CurriculumLessonVersion, CurriculumProgram, CurriculumUnit
from crownpath.curriculum_seed import CATALOGS, seed_legacy_curriculum
from crownpath.database import init_db, session


class CurriculumSeedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_seed_is_idempotent_and_preserves_canonical_content(self):
        first = seed_legacy_curriculum()
        second = seed_legacy_curriculum()
        self.assertGreaterEqual(first["programs"], 0)
        self.assertEqual(second, {"programs": 0, "courses": 0, "units": 0, "lessons": 0, "versions": 0})

        db = session()
        try:
            for track, catalog in CATALOGS.items():
                slug = track.lower().replace("_", "-")
                program = db.scalar(select(CurriculumProgram).where(CurriculumProgram.slug == slug))
                self.assertIsNotNone(program)
                course = db.scalar(select(CurriculumCourse).where(CurriculumCourse.program_id == program.program_id))
                self.assertIsNotNone(course)
                unit = db.scalar(select(CurriculumUnit).where(CurriculumUnit.course_id == course.course_id))
                self.assertIsNotNone(unit)
                for lesson_id, _ in catalog:
                    lesson = db.get(CurriculumLesson, lesson_id)
                    self.assertIsNotNone(lesson)
                    version = db.scalar(select(CurriculumLessonVersion).where(
                        CurriculumLessonVersion.lesson_id == lesson_id,
                        CurriculumLessonVersion.version == 1,
                    ))
                    self.assertIsNotNone(version)
                    self.assertTrue(version.content_json)
                    self.assertFalse(version.approved)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
