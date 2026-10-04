import inspect
import unittest

from crownpath import owner_curriculum


OWNER = {"user_id": "owner-1", "role": "OWNER", "active": True}
INSTRUCTOR = {"user_id": "instructor-1", "role": "INSTRUCTOR", "active": True}
LEARNER = {"user_id": "learner-1", "role": "BARBER", "active": True}


class OwnerCurriculumSecurityTest(unittest.TestCase):
    def test_owner_is_allowed(self):
        owner_curriculum.require_owner(OWNER)

    def test_non_owners_are_denied(self):
        for user in (INSTRUCTOR, LEARNER, None):
            with self.assertRaises(PermissionError):
                owner_curriculum.require_owner(user)

    def test_slug_validation_is_restrictive(self):
        self.assertEqual(owner_curriculum.validate_slug("hair-science-101"), "hair-science-101")
        for slug in ("Hair Science", "../admin", "hair--science", "hair_science"):
            with self.assertRaises(ValueError):
                owner_curriculum.validate_slug(slug)

    def test_new_programs_are_forced_to_draft(self):
        source = inspect.getsource(owner_curriculum.create_draft_program)
        self.assertIn("status=DRAFT_STATUS", source)
        self.assertEqual(owner_curriculum.DRAFT_STATUS, "DRAFT")

    def test_service_has_no_publish_or_release_operation(self):
        public_names = {name.lower() for name in dir(owner_curriculum) if not name.startswith("_")}
        self.assertNotIn("publish", public_names)
        self.assertNotIn("release", public_names)

    def test_locked_scalp_ai_functionality_is_absent(self):
        source = inspect.getsource(owner_curriculum).lower()
        self.assertNotIn("ai-assisted", source)
        self.assertNotIn("condition detection", source)
        self.assertNotIn("scalp camera", source)


if __name__ == "__main__":
    unittest.main()
