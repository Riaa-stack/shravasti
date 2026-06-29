import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class TrendReport(Base):
    __tablename__ = "trend_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    scope_paper_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    topics: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    emerging_keywords: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    popular_methods: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    publication_timeline: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
