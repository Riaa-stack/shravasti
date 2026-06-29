import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class ResearchGap(Base):
    __tablename__ = "research_gaps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True, nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    future_scope: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    missing_areas: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    unsolved_problems: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    improvement_opportunities: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
