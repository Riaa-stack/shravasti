from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
from app.models.paper import PaperStatus, DifficultyLevel

class PaperBase(BaseModel):
    title: Optional[str] = None
    authors: Optional[list[str]] = None
    publication_year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    category: Optional[str] = None

class PaperCreate(BaseModel):
    file_path: str
    status: PaperStatus = PaperStatus.uploaded

class PaperUpdate(BaseModel):
    category: Optional[str] = None

class PaperResponse(PaperBase):
    id: uuid.UUID
    user_id: uuid.UUID
    difficulty_level: Optional[DifficultyLevel] = None
    page_count: Optional[int] = None
    status: PaperStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
