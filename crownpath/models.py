from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from crownpath.db_engine import Base

def now_utc(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__="users"
    user_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    name: Mapped[str]=mapped_column(String(120),nullable=False)
    email: Mapped[str]=mapped_column(String(255),unique=True,nullable=False,index=True)
    password_hash: Mapped[str]=mapped_column(Text,nullable=False)
    role: Mapped[str]=mapped_column(String(50),nullable=False,default="HOME_CARE")
    track: Mapped[str|None]=mapped_column(String(50))
    active: Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    email_verified: Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)
    mfa_enabled: Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)
    mfa_secret: Mapped[str|None]=mapped_column(Text)
    failed_login_attempts: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    locked_until: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)

class InstructorRequest(Base):
    __tablename__="instructor_requests"
    request_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[str]=mapped_column(String(64),ForeignKey("users.user_id"),nullable=False,index=True)
    statement: Mapped[str|None]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(20),nullable=False,default="PENDING",index=True)
    reviewed_by: Mapped[str|None]=mapped_column(String(64),ForeignKey("users.user_id"))
    review_note: Mapped[str|None]=mapped_column(Text)
    reviewed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc,index=True)

class LearnerProgress(Base):
    __tablename__="learner_progress"
    __table_args__=(UniqueConstraint("user_id","lesson_id",name="uq_learner_lesson_progress"),)
    progress_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[str]=mapped_column(String(64),ForeignKey("users.user_id"),nullable=False,index=True)
    lesson_id: Mapped[str]=mapped_column(String(100),nullable=False,index=True)
    status: Mapped[str]=mapped_column(String(20),nullable=False,default="NOT_STARTED")
    progress_percent: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    opened_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)

class LearnerLessonStep(Base):
    __tablename__="learner_lesson_steps"
    __table_args__=(UniqueConstraint("user_id","lesson_id","step_index",name="uq_learner_lesson_step"),)
    step_progress_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[str]=mapped_column(String(64),ForeignKey("users.user_id"),nullable=False,index=True)
    lesson_id: Mapped[str]=mapped_column(String(100),nullable=False,index=True)
    step_index: Mapped[int]=mapped_column(Integer,nullable=False)
    completed: Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)

class AuthToken(Base):
    __tablename__="auth_tokens"
    token_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[str]=mapped_column(String(64),ForeignKey("users.user_id"),nullable=False,index=True)
    token_hash: Mapped[str]=mapped_column(String(128),unique=True,nullable=False)
    token_type: Mapped[str]=mapped_column(String(50),nullable=False)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    used_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)

class ResourceAssignment(Base):
    __tablename__="resource_assignments"
    __table_args__=(UniqueConstraint("user_id","resource_type","resource_id","access_level",name="uq_resource_assignment"),)
    assignment_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id: Mapped[str]=mapped_column(String(64),nullable=False,index=True)
    resource_type: Mapped[str]=mapped_column(String(50),nullable=False,index=True)
    resource_id: Mapped[str]=mapped_column(String(100),nullable=False,index=True)
    access_level: Mapped[str]=mapped_column(String(20),nullable=False,default="VIEW")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)

class AuditEvent(Base):
    __tablename__="audit_events"
    audit_id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    user_id: Mapped[str|None]=mapped_column(String(64),index=True)
    action: Mapped[str]=mapped_column(String(120),nullable=False)
    category: Mapped[str|None]=mapped_column(String(80))
    resource_type: Mapped[str|None]=mapped_column(String(50))
    resource_id: Mapped[str|None]=mapped_column(String(100))
    result: Mapped[str]=mapped_column(String(40),nullable=False)
    reason: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc,index=True)

class AudioStation(Base):
    __tablename__="audio_stations"
    station_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    name: Mapped[str]=mapped_column(String(120),nullable=False)
    category: Mapped[str]=mapped_column(String(50),nullable=False)
    source_type: Mapped[str]=mapped_column(String(50),nullable=False,default="LICENSED_STREAM")
    source_reference: Mapped[str|None]=mapped_column(Text)
    enabled: Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    client_facing: Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)

class AudioZone(Base):
    __tablename__="audio_zones"
    zone_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    name: Mapped[str]=mapped_column(String(120),nullable=False)
    location_type: Mapped[str]=mapped_column(String(60),nullable=False)
    station_id: Mapped[str|None]=mapped_column(String(64),ForeignKey("audio_stations.station_id"))
    volume: Mapped[int]=mapped_column(Integer,nullable=False,default=35)
    muted: Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)
    enabled: Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)

class AudioSchedule(Base):
    __tablename__="audio_schedules"
    schedule_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    zone_id: Mapped[str]=mapped_column(String(64),ForeignKey("audio_zones.zone_id"),nullable=False,index=True)
    day_of_week: Mapped[str]=mapped_column(String(12),nullable=False)
    start_time: Mapped[str]=mapped_column(String(5),nullable=False)
    end_time: Mapped[str]=mapped_column(String(5),nullable=False)
    station_id: Mapped[str]=mapped_column(String(64),ForeignKey("audio_stations.station_id"),nullable=False)
    enabled: Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)

class AudioDevice(Base):
    __tablename__="audio_devices"
    device_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    name: Mapped[str]=mapped_column(String(120),nullable=False)
    device_type: Mapped[str]=mapped_column(String(60),nullable=False)
    provider: Mapped[str|None]=mapped_column(String(80))
    external_reference: Mapped[str|None]=mapped_column(Text)
    online: Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)
    max_volume: Mapped[int]=mapped_column(Integer,nullable=False,default=60)
    enabled: Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)

class AudioZoneDevice(Base):
    __tablename__="audio_zone_devices"
    __table_args__=(UniqueConstraint("zone_id","device_id",name="uq_audio_zone_device"),)
    mapping_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    zone_id: Mapped[str]=mapped_column(String(64),ForeignKey("audio_zones.zone_id"),nullable=False,index=True)
    device_id: Mapped[str]=mapped_column(String(64),ForeignKey("audio_devices.device_id"),nullable=False,index=True)
    primary_device: Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    enabled: Mapped[bool]=mapped_column(Boolean,nullable=False,default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)


class PracticalAssessment(Base):
    """Instructor-reviewed competency record; not a professional license."""
    __tablename__="practical_assessments"
    __table_args__=(
        CheckConstraint("knowledge_percent >= 0 AND knowledge_percent <= 100", name="ck_practical_assessment_knowledge_range"),
        CheckConstraint("decision IN ('APPROVED', 'REJECTED', 'REVIEW_REQUIRED')", name="ck_practical_assessment_decision"),
        CheckConstraint("learner_id <> reviewer_id", name="ck_practical_assessment_distinct_reviewer"),
    )
    assessment_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    learner_id: Mapped[str]=mapped_column(String(64),ForeignKey("users.user_id"),nullable=False,index=True)
    reviewer_id: Mapped[str]=mapped_column(String(64),ForeignKey("users.user_id"),nullable=False,index=True)
    lesson_id: Mapped[str]=mapped_column(String(100),nullable=False,index=True)
    rubric_version: Mapped[str]=mapped_column(String(40),nullable=False)
    knowledge_percent: Mapped[int]=mapped_column(Integer,nullable=False)
    competency_scores_json: Mapped[str]=mapped_column(Text,nullable=False)
    safety_gates_json: Mapped[str]=mapped_column(Text,nullable=False)
    evidence_refs_json: Mapped[str]=mapped_column(Text,nullable=False)
    decision: Mapped[str]=mapped_column(String(30),nullable=False,default="REVIEW_REQUIRED")
    review_note: Mapped[str|None]=mapped_column(Text)
    reviewed_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)


class AssessmentEvidenceRecord(Base):
    """Server-issued evidence reference metadata; no image or video bytes."""
    __tablename__="assessment_evidence_records"
    evidence_id: Mapped[str]=mapped_column(String(64),primary_key=True)
    learner_id: Mapped[str]=mapped_column(String(64),ForeignKey("users.user_id"),nullable=False,index=True)
    lesson_id: Mapped[str]=mapped_column(String(100),nullable=False,index=True)
    evidence_type: Mapped[str]=mapped_column(String(30),nullable=False)
    storage_reference: Mapped[str]=mapped_column(String(255),nullable=False,unique=True)
    consent_confirmed: Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)
    revoked: Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)


class EvidenceStorageObject(Base):
    """Backend-issued storage metadata, never authoritative from client input."""
    __tablename__="evidence_storage_objects"
    storage_reference: Mapped[str]=mapped_column(String(255),primary_key=True)
    learner_id: Mapped[str]=mapped_column(String(64),ForeignKey("users.user_id"),nullable=False,index=True)
    lesson_id: Mapped[str]=mapped_column(String(100),nullable=False)
    evidence_type: Mapped[str]=mapped_column(String(30),nullable=False)
    upload_complete: Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)
    revoked: Mapped[bool]=mapped_column(Boolean,nullable=False,default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,default=now_utc)
