import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, Enum, ForeignKey, Integer, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User

class PaperStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    processed = "processed"
    failed = "failed"

class DifficultyLevel(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=True)
    authors: Mapped[list[str]] = mapped_column(JSONB, nullable=True)
    publication_year: Mapped[int] = mapped_column(Integer, nullable=True)
    venue: Mapped[str] = mapped_column(String(500), nullable=True)
    doi: Mapped[str] = mapped_column(String(255), nullable=True)
    abstract: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(255), nullable=True)
    difficulty_level: Mapped[DifficultyLevel] = mapped_column(Enum(DifficultyLevel), nullable=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[PaperStatus] = mapped_column(Enum(PaperStatus), default=PaperStatus.uploaded, index=True, nullable=False)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    flag_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_available_for_ai: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", lazy="selectin")
    chunks: Mapped[list["PaperChunk"]] = relationship("PaperChunk", back_populates="paper", cascade="all, delete-orphan")
