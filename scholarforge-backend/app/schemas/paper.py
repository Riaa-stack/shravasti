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
    is_flagged: bool = False
    flag_reason: Optional[str] = None
    is_available_for_ai: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class PaperWithUserResponse(PaperResponse):
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None

class PaperFlagUpdate(BaseModel):
    is_flagged: Optional[bool] = None
    flag_reason: Optional[str] = None
    is_available_for_ai: Optional[bool] = None
