import os
import unittest
import uuid

os.environ.setdefault("CROWNPATH_ENV", "staging")
os.environ.setdefault("CROWNPATH_SECRET_KEY", "ci-only-secret-key-for-curriculum-publish-tests-123456789")

from fastapi.testclient import TestClient
from sqlalchemy import select

from crownpath.auth import create_access_token, create_user, set_user_role
from crownpath.curriculum_models import CurriculumLesson, CurriculumLessonVersion, LearnerMastery, LearnerMasteryEvidence
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

    def test_mastery_update_requires_evidence_and_records_verifier_and_audit(self):
        learner=create_user("Mastery Learner",f"mastery-learner-{uuid.uuid4().hex[:10]}@example.com","CrownPath-Learner-Test-2026!","HOME_CARE")
        try:
            missing=self.client.put(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations",json={"level":"PRACTICED"})
            self.assertEqual(missing.status_code,422)
            invalid=self.client.put(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations",json={"level":"EXPERT","evidence_type":"ASSESSMENT","evidence_reference":"CP-EVIDENCE-1"})
            self.assertEqual(invalid.status_code,422)
            saved=self.client.put(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations",json={"level":"DEMONSTRATED","evidence_type":"PRACTICAL","evidence_reference":"CP-EVIDENCE-2","note":"Instructor-reviewed practical"})
            self.assertEqual(saved.status_code,200,saved.text)
            mastery=saved.json()["mastery"]
            self.assertEqual(mastery["level"],"DEMONSTRATED")
            self.assertEqual(mastery["verified_by"],self.user["user_id"])
            self.assertTrue(mastery["verified_at"])
            db=session()
            try:
                audit=db.scalar(select(AuditEvent).where(AuditEvent.action=="LEARNER_MASTERY_UPDATED",AuditEvent.resource_id==mastery["mastery_id"]))
                self.assertIsNotNone(audit)
                self.assertEqual(audit.user_id,self.user["user_id"])
            finally: db.close()
        finally:
            db=session()
            try:
                db.query(LearnerMasteryEvidence).filter(LearnerMasteryEvidence.user_id==learner["user_id"]).delete(synchronize_session=False)\n                db.query(LearnerMastery).filter(LearnerMastery.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.query(AuthToken).filter(AuthToken.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.query(User).filter(User.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.commit()
            finally: db.close()

    def test_mastery_enforces_pathway_and_allows_shared_lessons(self):
        learner=create_user("Pathway Learner",f"pathway-learner-{uuid.uuid4().hex[:10]}@example.com","CrownPath-Learner-Test-2026!","HOME_CARE")
        try:
            own=self.client.put(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations",json={"level":"PRACTICED","evidence_type":"ASSESSMENT","evidence_reference":"CP-PATH-OWN"})
            self.assertEqual(own.status_code,200,own.text)
            shared=self.client.put(f"/api/owner/mastery/{learner['user_id']}/wellness-client-experience",json={"level":"PRACTICED","evidence_type":"PROJECT","evidence_reference":"CP-PATH-SHARED"})
            self.assertEqual(shared.status_code,200,shared.text)
            blocked=self.client.put(f"/api/owner/mastery/{learner['user_id']}/barber-foundations",json={"level":"PRACTICED","evidence_type":"ASSESSMENT","evidence_reference":"CP-PATH-WRONG"})
            self.assertEqual(blocked.status_code,409,blocked.text)
            self.assertIn("not assigned",blocked.json()["detail"])
        finally:
            db=session()
            try:
                db.query(LearnerMasteryEvidence).filter(LearnerMasteryEvidence.user_id==learner["user_id"]).delete(synchronize_session=False)\n                db.query(LearnerMastery).filter(LearnerMastery.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.query(AuthToken).filter(AuthToken.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.query(User).filter(User.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.commit()
            finally: db.close()

    def test_mastery_progression_allows_forward_and_same_level_but_blocks_downgrade(self):
        learner=create_user("Progression Learner",f"progression-learner-{uuid.uuid4().hex[:10]}@example.com","CrownPath-Learner-Test-2026!","HOME_CARE")
        try:
            first=self.client.put(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations",json={"level":"PRACTICED","evidence_type":"ASSESSMENT","evidence_reference":"CP-PROG-1"})
            self.assertEqual(first.status_code,200,first.text)
            mastery_id=first.json()["mastery"]["mastery_id"]
            refresh=self.client.put(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations",json={"level":"PRACTICED","evidence_type":"PROJECT","evidence_reference":"CP-PROG-2"})
            self.assertEqual(refresh.status_code,200,refresh.text)
            self.assertEqual(refresh.json()["mastery"]["mastery_id"],mastery_id)
            self.assertEqual(refresh.json()["mastery"]["evidence_reference"],"CP-PROG-2")
            forward=self.client.put(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations",json={"level":"DEMONSTRATED","evidence_type":"PRACTICAL","evidence_reference":"CP-PROG-3"})
            self.assertEqual(forward.status_code,200,forward.text)
            blocked=self.client.put(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations",json={"level":"INTRODUCED","evidence_type":"ASSESSMENT","evidence_reference":"CP-PROG-4"})
            self.assertEqual(blocked.status_code,409,blocked.text)
            self.assertIn("cannot be downgraded",blocked.json()["detail"])
            db=session()
            try:
                saved=db.scalar(select(LearnerMastery).where(LearnerMastery.user_id==learner["user_id"],LearnerMastery.lesson_id=="home-care-foundations"))
                self.assertEqual(saved.level,"DEMONSTRATED")
                self.assertEqual(saved.evidence_reference,"CP-PROG-3")
            finally: db.close()
        finally:
            db=session()
            try:
                db.query(LearnerMasteryEvidence).filter(LearnerMasteryEvidence.user_id==learner["user_id"]).delete(synchronize_session=False)\n                db.query(LearnerMastery).filter(LearnerMastery.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.query(AuthToken).filter(AuthToken.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.query(User).filter(User.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.commit()
            finally: db.close()

    def test_mastery_rejects_whitespace_only_evidence(self):
        learner=create_user("Evidence Learner",f"evidence-learner-{uuid.uuid4().hex[:10]}@example.com","CrownPath-Learner-Test-2026!","HOME_CARE")
        try:
            blank_type=self.client.put(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations",json={"level":"PRACTICED","evidence_type":"   ","evidence_reference":"CP-EVIDENCE-VALID"})
            self.assertEqual(blank_type.status_code,422,blank_type.text)
            blank_reference=self.client.put(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations",json={"level":"PRACTICED","evidence_type":"ASSESSMENT","evidence_reference":"   "})
            self.assertEqual(blank_reference.status_code,422,blank_reference.text)
            db=session()
            try:
                saved=db.scalar(select(LearnerMastery).where(LearnerMastery.user_id==learner["user_id"],LearnerMastery.lesson_id=="home-care-foundations"))
                self.assertIsNone(saved)
            finally: db.close()
        finally:
            db=session()
            try:
                db.query(AuthToken).filter(AuthToken.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.query(User).filter(User.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.commit()
            finally: db.close()

    def test_owner_can_read_current_mastery_without_mutating_it(self):
        learner=create_user("Lookup Learner",f"lookup-learner-{uuid.uuid4().hex[:10]}@example.com","CrownPath-Learner-Test-2026!","HOME_CARE")
        try:
            empty=self.client.get(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations")
            self.assertEqual(empty.status_code,200,empty.text)
            self.assertIsNone(empty.json()["mastery"])
            saved=self.client.put(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations",json={"level":"DEMONSTRATED","evidence_type":"PRACTICAL","evidence_reference":"CP-LOOKUP-1"})
            self.assertEqual(saved.status_code,200,saved.text)
            before=saved.json()["mastery"]
            found=self.client.get(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations")
            self.assertEqual(found.status_code,200,found.text)
            current=found.json()["mastery"]
            self.assertEqual(current["mastery_id"],before["mastery_id"])
            self.assertEqual(current["level"],"DEMONSTRATED")
            self.assertEqual(current["evidence_reference"],"CP-LOOKUP-1")
            self.assertEqual(current["verified_by"],self.user["user_id"])
            self.assertTrue(current["verified_by_name"])
            again=self.client.get(f"/api/owner/mastery/{learner['user_id']}/home-care-foundations").json()["mastery"]
            self.assertEqual(again["mastery_id"],current["mastery_id"])
            self.assertEqual(again["verified_at"],current["verified_at"])
        finally:
            db=session()
            try:
                db.query(LearnerMasteryEvidence).filter(LearnerMasteryEvidence.user_id==learner["user_id"]).delete(synchronize_session=False)\n                db.query(LearnerMastery).filter(LearnerMastery.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.query(AuthToken).filter(AuthToken.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.query(User).filter(User.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.commit()
            finally: db.close()

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


    def test_draft_can_be_saved_but_approved_version_is_immutable(self):
        lesson_id="home-care-foundations"
        db=session()
        try:
            lesson=db.get(CurriculumLesson,lesson_id)
            active=lesson.active_version
            source=db.scalar(select(CurriculumLessonVersion).where(CurriculumLessonVersion.lesson_id==lesson_id,CurriculumLessonVersion.version==active))
            import json
            content=json.loads(source.content_json)
        finally: db.close()

        created=self.client.post(f"/api/owner/curriculum/lessons/{lesson_id}/versions",json={"content":content,"note":"editable draft"})
        self.assertEqual(created.status_code,200,created.text)
        version=created.json()["version"]
        changed=dict(content); changed["owner_test_marker"]="saved draft only"
        saved=self.client.put(f"/api/owner/curriculum/lessons/{lesson_id}/versions/{version}",json={"content":changed,"note":"save draft test"})
        self.assertEqual(saved.status_code,200,saved.text)

        approved=self.client.post(f"/api/owner/curriculum/lessons/{lesson_id}/versions/{version}/approve",json={"note":"lock draft test"})
        self.assertEqual(approved.status_code,200,approved.text)
        blocked=self.client.put(f"/api/owner/curriculum/lessons/{lesson_id}/versions/{version}",json={"content":content,"note":"must fail"})
        self.assertEqual(blocked.status_code,409)

        db=session()
        try:
            draft=db.scalar(select(CurriculumLessonVersion).where(CurriculumLessonVersion.lesson_id==lesson_id,CurriculumLessonVersion.version==version))
            self.assertIn("owner_test_marker",json.loads(draft.content_json))
            actions=set(db.scalars(select(AuditEvent.action).where(AuditEvent.user_id==self.user["user_id"])).all())
            self.assertIn("CURRICULUM_VERSION_UPDATED",actions)
            db.delete(draft); db.commit()
        finally: db.close()

    def test_mastery_evidence_history_appends_only_successful_verifications(self):
        learner=create_user("Evidence History Learner",f"evidence-history-{uuid.uuid4().hex[:10]}@example.com","CrownPath-Learner-Test-2026!","HOME_CARE")
        lesson_id="home-care-foundations"
        try:
            first=self.client.put(f"/api/owner/mastery/{learner['user_id']}/{lesson_id}",json={"level":"PRACTICED","evidence_type":"ASSESSMENT","evidence_reference":"CP-HIST-1","note":"first evidence"})
            self.assertEqual(first.status_code,200,first.text)
            refresh=self.client.put(f"/api/owner/mastery/{learner['user_id']}/{lesson_id}",json={"level":"PRACTICED","evidence_type":"PROJECT","evidence_reference":"CP-HIST-2","note":"same level new evidence"})
            self.assertEqual(refresh.status_code,200,refresh.text)
            advanced=self.client.put(f"/api/owner/mastery/{learner['user_id']}/{lesson_id}",json={"level":"DEMONSTRATED","evidence_type":"PRACTICAL","evidence_reference":"CP-HIST-3","note":"forward progression"})
            self.assertEqual(advanced.status_code,200,advanced.text)
            db=session()
            try:
                rows=db.scalars(select(LearnerMasteryEvidence).where(LearnerMasteryEvidence.user_id==learner["user_id"],LearnerMasteryEvidence.lesson_id==lesson_id).order_by(LearnerMasteryEvidence.verified_at,LearnerMasteryEvidence.evidence_id)).all()
                self.assertEqual(len(rows),3)
                self.assertEqual([row.level for row in rows],["PRACTICED","PRACTICED","DEMONSTRATED"])
                self.assertEqual([row.evidence_reference for row in rows],["CP-HIST-1","CP-HIST-2","CP-HIST-3"])
                mastery_id=rows[0].mastery_id
                self.assertTrue(all(row.mastery_id==mastery_id for row in rows))
            finally: db.close()
            rejected=self.client.put(f"/api/owner/mastery/{learner['user_id']}/{lesson_id}",json={"level":"INTRODUCED","evidence_type":"ASSESSMENT","evidence_reference":"CP-HIST-REJECT"})
            self.assertEqual(rejected.status_code,409)
            db=session()
            try:
                count=len(db.scalars(select(LearnerMasteryEvidence).where(LearnerMasteryEvidence.user_id==learner["user_id"],LearnerMasteryEvidence.lesson_id==lesson_id)).all())
                self.assertEqual(count,3)
            finally: db.close()
        finally:
            db=session()
            try:
                db.query(LearnerMasteryEvidence).filter(LearnerMasteryEvidence.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.query(LearnerMasteryEvidence).filter(LearnerMasteryEvidence.user_id==learner["user_id"]).delete(synchronize_session=False)\n                db.query(LearnerMastery).filter(LearnerMastery.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.query(AuthToken).filter(AuthToken.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.query(User).filter(User.user_id==learner["user_id"]).delete(synchronize_session=False)
                db.commit()
            finally: db.close()

    def test_active_published_version_rejects_edit(self):
        lesson_id="home-care-foundations"
        db=session()
        try:
            lesson=db.get(CurriculumLesson,lesson_id)
            version=db.scalar(select(CurriculumLessonVersion).where(CurriculumLessonVersion.lesson_id==lesson_id,CurriculumLessonVersion.version==lesson.active_version))
            import json
            content=json.loads(version.content_json)
            lesson.status="PUBLISHED"; version.approved=False; version.approved_by=None; version.approved_at=None; db.commit()
            active=lesson.active_version
        finally: db.close()
        blocked=self.client.put(f"/api/owner/curriculum/lessons/{lesson_id}/versions/{active}",json={"content":content,"note":"must fail"})
        self.assertEqual(blocked.status_code,409)


if __name__=="__main__":
    unittest.main()
