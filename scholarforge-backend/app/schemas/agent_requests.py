from pydantic import BaseModel
from typing import List, Optional, Any
import uuid

class TaskRequest(BaseModel):
    paper_ids: List[str]
    query: Optional[str] = None

class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None

class ChatRequest(BaseModel):
    paper_ids: List[str]
    query: str
    session_id: Optional[str] = None
