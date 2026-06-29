import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Enum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class ReportType(str, enum.Enum):
    literature_review = "literature_review"
    gap_analysis = "gap_analysis"
    trend_report = "trend_report"
    citation_report = "citation_report"
    methodology = "methodology"

class ExportFormat(str, enum.Enum):
    pdf = "pdf"
    docx = "docx"
    pptx = "pptx"

class ExportReport(Base):
    __tablename__ = "export_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType), nullable=False)
    format: Mapped[ExportFormat] = mapped_column(Enum(ExportFormat), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
