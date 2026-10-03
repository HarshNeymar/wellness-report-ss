from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Copied out of teacher_input so we can filter/sort reports by class and year
    student_name: Mapped[str] = mapped_column(String(80), index=True)
    class_name: Mapped[str] = mapped_column(String(20), index=True)
    academic_year: Mapped[str] = mapped_column(String(7), index=True)
    roll_number: Mapped[str] = mapped_column(String(10))

    teacher_input: Mapped[dict] = mapped_column(JSON)               # what the teacher entered
    ai_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # what the AI wrote

    status: Mapped[str] = mapped_column(String(12), default="draft")  # draft | generated | failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
