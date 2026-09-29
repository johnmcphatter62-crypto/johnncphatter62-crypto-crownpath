import inspect
import unittest

from crownpath import curriculum_models as models


class CurriculumModelIsolationTest(unittest.TestCase):
    def test_expected_structural_models_exist(self):
        expected = {
            "CurriculumProgram",
            "CurriculumCourse",
            "CurriculumUnit",
            "CurriculumLesson",
            "CurriculumUnitLesson",
            "CurriculumLessonVersion",
            "CurriculumActivity",
            "CurriculumAssessment",
        }
        for name in expected:
            self.assertTrue(hasattr(models, name), name)

    def test_curriculum_defaults_remain_draft_and_unapproved(self):
        self.assertEqual(models.CurriculumProgram.__table__.c.status.default.arg, "DRAFT")
        self.assertEqual(models.CurriculumCourse.__table__.c.status.default.arg, "DRAFT")
        self.assertEqual(models.CurriculumLesson.__table__.c.status.default.arg, "DRAFT")
        self.assertFalse(models.CurriculumLessonVersion.__table__.c.approved.default.arg)

    def test_isolated_layer_excludes_enrollment_and_mastery_models(self):
        self.assertFalse(hasattr(models, "CourseEnrollment"))
        self.assertFalse(hasattr(models, "LearnerMastery"))
        self.assertFalse(hasattr(models, "LearnerMasteryEvidence"))

    def test_locked_scalp_ai_functionality_is_not_in_model_layer(self):
        source = inspect.getsource(models).lower()
        self.assertNotIn("ai-assisted", source)
        self.assertNotIn("scalp camera", source)
        self.assertNotIn("condition detection", source)


if __name__ == "__main__":
    unittest.main()
