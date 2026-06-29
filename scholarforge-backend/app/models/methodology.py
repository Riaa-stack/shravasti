import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class MethodologyAnalysis(Base):
    __tablename__ = "methodology_analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    paper_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True, nullable=False)
    algorithms: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    models: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    datasets: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    evaluation_metrics: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    experimental_setup: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
