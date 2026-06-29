import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class CitationStyle(str, enum.Enum):
    ieee = "ieee"
    apa = "apa"
    mla = "mla"
    harvard = "harvard"

class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True, nullable=False)
    style: Mapped[CitationStyle] = mapped_column(Enum(CitationStyle), nullable=False)
    formatted_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
