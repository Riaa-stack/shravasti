from typing import Any
import uuid
import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, CurrentUser
from app.models.paper import Paper, PaperStatus
from app.schemas.paper import PaperResponse, PaperUpdate
from app.core.config import settings
from app.tasks.ingestion_tasks import process_paper_task

router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

@router.post("/upload", response_model=list[PaperResponse])
async def upload_papers(
    session: SessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
) -> Any:
    """Upload one or more research papers (PDF)."""
    uploaded_papers = []
    
    # Ensure storage directory exists
    user_storage_dir = os.path.join(settings.PAPERS_STORAGE_DIR, str(current_user.id))
    os.makedirs(user_storage_dir, exist_ok=True)
    
    for file in files:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF")
            
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds maximum size of 50MB")
            
        paper_id = uuid.uuid4()
        file_path = os.path.join(user_storage_dir, f"{paper_id}.pdf")
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save file {file.filename}")
            
        paper = Paper(
            id=paper_id,
            user_id=current_user.id,
            title=file.filename,
            file_path=file_path,
            status=PaperStatus.uploaded
        )
        session.add(paper)
        uploaded_papers.append(paper)
        
    await session.commit()
    
    for paper in uploaded_papers:
        await session.refresh(paper)
        background_tasks.add_task(process_paper_task, str(paper.id))
        
    return uploaded_papers

@router.get("/", response_model=list[PaperResponse])
async def read_papers(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """Retrieve user's papers."""
    stmt = select(Paper).where(Paper.user_id == current_user.id).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/{paper_id}", response_model=PaperResponse)
async def read_paper(
    paper_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get a specific paper by id."""
    stmt = select(Paper).where(Paper.id == paper_id, Paper.user_id == current_user.id)
    result = await session.execute(stmt)
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper

@router.patch("/{paper_id}/category", response_model=PaperResponse)
async def update_paper_category(
    paper_id: uuid.UUID,
    paper_in: PaperUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Update paper category."""
    stmt = select(Paper).where(Paper.id == paper_id, Paper.user_id == current_user.id)
    result = await session.execute(stmt)
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    if paper_in.category is not None:
        paper.category = paper_in.category
        
    session.add(paper)
    await session.commit()
    await session.refresh(paper)
    return paper

@router.delete("/{paper_id}")
async def delete_paper(
    paper_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Delete a paper."""
    stmt = select(Paper).where(Paper.id == paper_id, Paper.user_id == current_user.id)
    result = await session.execute(stmt)
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    # Delete file from disk
    if os.path.exists(paper.file_path):
        os.remove(paper.file_path)
        
    await session.delete(paper)
    await session.commit()
    return {"status": "ok"}
