"""Database-backed CrownPath curriculum hierarchy.

These tables sit alongside the legacy code-defined lesson catalog so curriculum
can be migrated incrementally without breaking existing learner progress.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from crownpath.db_engine import Base


def now_utc():
    return datetime.now(timezone.utc)


class CurriculumProgram(Base):
    __tablename__ = "curriculum_programs"
    program_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class CurriculumCourse(Base):
    __tablename__ = "curriculum_courses"
    course_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    program_id: Mapped[str] = mapped_column(String(64), ForeignKey("curriculum_programs.program_id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    __table_args__ = (UniqueConstraint("program_id", "slug", name="uq_curriculum_course_slug"),)


class CurriculumUnit(Base):
    __tablename__ = "curriculum_units"
    unit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(64), ForeignKey("curriculum_courses.course_id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    description: Mapped[str | None] = mapped_column(Text)


class CurriculumLesson(Base):
    __tablename__ = "curriculum_lessons"
    lesson_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    unit_id: Mapped[str] = mapped_column(String(64), ForeignKey("curriculum_units.unit_id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")


class CurriculumUnitLesson(Base):
    """Places one canonical lesson in one or more curriculum units."""
    __tablename__ = "curriculum_unit_lessons"
    __table_args__ = (UniqueConstraint("unit_id", "lesson_id", name="uq_curriculum_unit_lesson"),)
    assignment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    unit_id: Mapped[str] = mapped_column(String(64), ForeignKey("curriculum_units.unit_id"), nullable=False, index=True)
    lesson_id: Mapped[str] = mapped_column(String(100), ForeignKey("curriculum_lessons.lesson_id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CurriculumLessonVersion(Base):
    __tablename__ = "curriculum_lesson_versions"
    __table_args__ = (UniqueConstraint("lesson_id", "version", name="uq_curriculum_lesson_version"),)
    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lesson_id: Mapped[str] = mapped_column(String(100), ForeignKey("curriculum_lessons.lesson_id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="CROWNPATH")
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.user_id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


class CurriculumActivity(Base):
    __tablename__ = "curriculum_activities"
    activity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lesson_id: Mapped[str] = mapped_column(String(100), ForeignKey("curriculum_lessons.lesson_id"), nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CurriculumAssessment(Base):
    __tablename__ = "curriculum_assessments"
    assessment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lesson_id: Mapped[str] = mapped_column(String(100), ForeignKey("curriculum_lessons.lesson_id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(40), nullable=False, default="KNOWLEDGE_CHECK")
    mastery_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_course_enrollment"),)
    enrollment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(64), ForeignKey("curriculum_courses.course_id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LearnerMastery(Base):
    __tablename__ = "learner_mastery"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_learner_mastery"),)
    mastery_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    lesson_id: Mapped[str] = mapped_column(String(100), ForeignKey("curriculum_lessons.lesson_id"), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="INTRODUCED")
    evidence_type: Mapped[str | None] = mapped_column(String(40))
    evidence_reference: Mapped[str | None] = mapped_column(String(120))
    verified_by: Mapped[str | None] = mapped_column(String(64), ForeignKey("users.user_id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class LearnerMasteryEvidence(Base):
    __tablename__ = "learner_mastery_evidence"
    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mastery_id: Mapped[str] = mapped_column(String(64), ForeignKey("learner_mastery.mastery_id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    lesson_id: Mapped[str] = mapped_column(String(100), ForeignKey("curriculum_lessons.lesson_id"), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    verified_by: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

