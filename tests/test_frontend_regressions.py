import unittest
from pathlib import Path


class FrontendRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.app_js = (root / "frontend" / "app.js").read_text(encoding="utf-8")
        cls.index_html = (root / "frontend" / "index.html").read_text(encoding="utf-8")

    def test_learner_ui_does_not_call_bulk_complete_endpoint(self):
        self.assertNotIn("/complete`,{method:'POST'", self.app_js)
        self.assertNotIn("/complete\",{method:\"POST\"", self.app_js)
        self.assertNotIn("completeLesson(", self.app_js)

    def test_step_completion_endpoint_remains_available_in_ui(self):
        self.assertIn("/steps/${stepIndex}/complete", self.app_js)
        self.assertIn("completeLessonStep(", self.app_js)

    def test_lesson_complete_control_cannot_submit_bulk_completion(self):
        self.assertIn("complete.disabled=true", self.app_js)
        self.assertNotIn("#lessonComplete').addEventListener('click'", self.app_js)

    def test_recovery_login_field_accepts_six_or_eight_digits(self):
        self.assertIn('pattern="[0-9]{6,8}"', self.index_html)
        self.assertIn('maxlength="8"', self.index_html)


if __name__ == "__main__":
    unittest.main()
