import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Enum, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class IdeaType(str, enum.Enum):
    project = "project"
    thesis = "thesis"
    publication = "publication"
    startup = "startup"
    topic = "topic"

class ResearchIdea(Base):
    __tablename__ = "research_ideas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    source_paper_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    idea_type: Mapped[IdeaType] = mapped_column(Enum(IdeaType), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
