"""Isolated metadata for CrownPath-managed teaching files.

This is NOT a file upload or storage implementation. Import explicitly in
synthetic SQLite tests; production migrations require separate review.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from crownpath.db_engine import Base


def now_utc():
    return datetime.now(timezone.utc)


class TeachingMaterial(Base):
    __tablename__ = "teaching_materials"

    material_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lesson_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("curriculum_lessons.lesson_id"), nullable=False, index=True
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc
    )


class TeachingMaterialVersion(Base):
    __tablename__ = "teaching_material_versions"
    __table_args__ = (
        UniqueConstraint("material_id", "version", name="uq_teaching_material_version"),
    )

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    material_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("teaching_materials.material_id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    submitted_by_user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id"), nullable=False
    )
    # Opaque object reference only. No file bytes or public download URL.
    storage_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    sha256_hex: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by_user_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.user_id")
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=now_utc
    )
