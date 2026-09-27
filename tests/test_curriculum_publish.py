import os
import unittest
import uuid

os.environ.setdefault("CROWNPATH_ENV", "staging")
os.environ.setdefault("CROWNPATH_SECRET_KEY", "ci-only-secret-key-for-curriculum-publish-tests-123456789")

from fastapi.testclient import TestClient
from sqlalchemy import select

from crownpath.auth import create_access_token, create_user, set_user_role
from crownpath.curriculum_models import CurriculumLesson, CurriculumLessonVersion
from crownpath.curriculum_seed import seed_legacy_curriculum
from crownpath.database import init_db, session
from crownpath.main import app
from crownpath.models import AuditEvent, AuthToken, User


class CurriculumPublishGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_legacy_curriculum()
        cls.client = TestClient(app)

    def setUp(self):
        suffix=uuid.uuid4().hex[:10]
        self.user=create_user("Curriculum Owner Test",f"curriculum-owner-{suffix}@example.com","CrownPath-Owner-Test-2026!","HOME_CARE")
        db=session()
        try:
            item=db.get(User,self.user["user_id"])
            item.role="OWNER"; item.track="OWNER"; db.commit()
        finally: db.close()
        token=create_access_token(self.user["user_id"])
        self.client.cookies.set("crownpath_session",token)

    def tearDown(self):
        db=session()
        try:
            versions=list(db.scalars(select(CurriculumLessonVersion).where(
                CurriculumLessonVersion.approved_by==self.user["user_id"]
            )).all())
            for version in versions:
                lesson=db.get(CurriculumLesson,version.lesson_id)
                version.approved=False
                version.approved_by=None
                version.approved_at=None
                if lesson:
                    lesson.status="DRAFT"
                    lesson.active_version=1
            db.flush()
            db.query(AuditEvent).filter(
                AuditEvent.user_id==self.user["user_id"],
                AuditEvent.category=="CURRICULUM",
            ).delete(synchronize_session=False)
            db.query(AuthToken).filter(AuthToken.user_id==self.user["user_id"]).delete()
            db.flush()
            db.query(User).filter(User.user_id==self.user["user_id"]).delete()
            db.commit()
        finally:
            db.close()
        self.client.cookies.clear()

    def test_publish_requires_approval_and_audits_success(self):
        lesson_id="home-care-foundations"
        db=session()
        try:
            lesson=db.get(CurriculumLesson,lesson_id)
            version=db.scalar(select(CurriculumLessonVersion).where(CurriculumLessonVersion.lesson_id==lesson_id,CurriculumLessonVersion.version==1))
            lesson.status="DRAFT"; version.approved=False; version.approved_by=None; version.approved_at=None; db.commit()
        finally: db.close()

        blocked=self.client.post(f"/api/owner/curriculum/lessons/{lesson_id}/versions/1/publish",json={"note":"blocked test"})
        self.assertEqual(blocked.status_code,409)

        approved=self.client.post(f"/api/owner/curriculum/lessons/{lesson_id}/versions/1/approve",json={"note":"review complete"})
        self.assertEqual(approved.status_code,200,approved.text)

        published=self.client.post(f"/api/owner/curriculum/lessons/{lesson_id}/versions/1/publish",json={"note":"publish approved"})
        self.assertEqual(published.status_code,200,published.text)

        db=session()
        try:
            lesson=db.get(CurriculumLesson,lesson_id)
            self.assertEqual(lesson.status,"PUBLISHED")
            actions=set(db.scalars(select(AuditEvent.action).where(AuditEvent.resource_id==lesson_id)).all())
            self.assertIn("CURRICULUM_VERSION_PUBLISH_BLOCKED",actions)
            self.assertIn("CURRICULUM_VERSION_APPROVED",actions)
            self.assertIn("CURRICULUM_VERSION_PUBLISHED",actions)
        finally: db.close()


    def test_new_version_is_draft_and_does_not_replace_active_version(self):
        lesson_id="home-care-foundations"
        db=session()
        try:
            lesson=db.get(CurriculumLesson,lesson_id)
            original_active=lesson.active_version
            source=db.scalar(select(CurriculumLessonVersion).where(CurriculumLessonVersion.lesson_id==lesson_id,CurriculumLessonVersion.version==original_active))
            import json
            content=json.loads(source.content_json)
        finally: db.close()

        created=self.client.post(f"/api/owner/curriculum/lessons/{lesson_id}/versions",json={"content":content,"note":"draft edit test"})
        self.assertEqual(created.status_code,200,created.text)
        data=created.json()
        self.assertFalse(data["approved"])
        self.assertFalse(data["published"])
        self.assertEqual(data["active_version"],original_active)

        db=session()
        try:
            lesson=db.get(CurriculumLesson,lesson_id)
            draft=db.scalar(select(CurriculumLessonVersion).where(CurriculumLessonVersion.lesson_id==lesson_id,CurriculumLessonVersion.version==data["version"]))
            self.assertEqual(lesson.active_version,original_active)
            self.assertIsNotNone(draft)
            self.assertFalse(draft.approved)
            self.assertEqual(draft.source_type,"CROWNPATH_OWNER_EDIT")
            action=db.scalar(select(AuditEvent.action).where(AuditEvent.user_id==self.user["user_id"],AuditEvent.action=="CURRICULUM_VERSION_CREATED"))
            self.assertEqual(action,"CURRICULUM_VERSION_CREATED")
            db.delete(draft); db.commit()
        finally: db.close()


if __name__=="__main__":
    unittest.main()
