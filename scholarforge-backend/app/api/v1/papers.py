from typing import Any
import uuid
import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, CurrentUser, require_role
from app.models.user import User, UserRole
from app.models.paper import Paper, PaperStatus
from app.schemas.paper import PaperResponse, PaperUpdate, PaperWithUserResponse, PaperFlagUpdate
from app.core.config import settings
from app.tasks.ingestion_tasks import process_paper_task

router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

def map_paper_with_user(paper: Paper) -> PaperWithUserResponse:
    user_name = paper.user.name if paper.user else None
    user_email = paper.user.email if paper.user else None
    user_role = paper.user.role.value if (paper.user and hasattr(paper.user.role, "value")) else (str(paper.user.role) if paper.user else None)
    
    return PaperWithUserResponse(
        id=paper.id,
        user_id=paper.user_id,
        title=paper.title,
        authors=paper.authors,
        publication_year=paper.publication_year,
        venue=paper.venue,
        doi=paper.doi,
        abstract=paper.abstract,
        category=paper.category,
        difficulty_level=paper.difficulty_level,
        page_count=paper.page_count,
        status=paper.status,
        is_flagged=paper.is_flagged,
        flag_reason=paper.flag_reason,
        is_available_for_ai=paper.is_available_for_ai,
        created_at=paper.created_at,
        updated_at=paper.updated_at,
        user_name=user_name,
        user_email=user_email,
        user_role=user_role,
    )

@router.post("/upload", response_model=list[PaperResponse])
async def upload_papers(
    session: SessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
) -> Any:
    """Upload one or more research papers (PDF)."""
    uploaded_papers = []
    
    # Ensure storage directory exists with safe fallback
    storage_root = settings.PAPERS_STORAGE_DIR
    try:
        os.makedirs(storage_root, exist_ok=True)
    except Exception:
        storage_root = os.path.abspath(os.path.join(".", "data", "papers"))
        os.makedirs(storage_root, exist_ok=True)
        
    user_storage_dir = os.path.join(storage_root, str(current_user.id))
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
    query: str | None = None,
) -> Any:
    """Retrieve user's papers with optional keyword search."""
    stmt = select(Paper).where(Paper.user_id == current_user.id)
    if query and query.strip():
        search_pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            (Paper.title.ilike(search_pattern)) |
            (Paper.venue.ilike(search_pattern)) |
            (Paper.category.ilike(search_pattern))
        )
    stmt = stmt.order_by(Paper.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()

@router.get("/admin/all", response_model=list[PaperWithUserResponse])
async def read_all_papers_admin(
    session: SessionDep,
    skip: int = 0,
    limit: int = 200,
    query: str | None = None,
    _: User = Depends(require_role("admin"))
) -> Any:
    """Retrieve all papers across all users with uploader info and role (Admin only)."""
    stmt = select(Paper).options(selectinload(Paper.user))
    if query and query.strip():
        search_pattern = f"%{query.strip()}%"
        stmt = stmt.join(User, Paper.user_id == User.id).where(
            (Paper.title.ilike(search_pattern)) |
            (Paper.venue.ilike(search_pattern)) |
            (Paper.category.ilike(search_pattern)) |
            (User.name.ilike(search_pattern)) |
            (User.email.ilike(search_pattern))
        )
    stmt = stmt.order_by(Paper.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(stmt)
    papers = result.scalars().all()
    return [map_paper_with_user(p) for p in papers]

@router.patch("/admin/{paper_id}/flag", response_model=PaperWithUserResponse)
async def flag_paper_admin(
    paper_id: uuid.UUID,
    flag_in: PaperFlagUpdate,
    session: SessionDep,
    _: User = Depends(require_role("admin"))
) -> Any:
    """Flag a paper as harmful/inappropriate and/or toggle AI analysis availability (Admin only)."""
    stmt = select(Paper).options(selectinload(Paper.user)).where(Paper.id == paper_id)
    result = await session.execute(stmt)
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    if flag_in.is_flagged is not None:
        paper.is_flagged = flag_in.is_flagged
        if flag_in.is_flagged and flag_in.is_available_for_ai is None:
            # By default, flagged harm paper becomes unavailable for AI analysis
            paper.is_available_for_ai = False
            
    if flag_in.flag_reason is not None:
        paper.flag_reason = flag_in.flag_reason
        
    if flag_in.is_available_for_ai is not None:
        paper.is_available_for_ai = flag_in.is_available_for_ai
        
    session.add(paper)
    await session.commit()
    await session.refresh(paper)
    return map_paper_with_user(paper)

@router.delete("/admin/{paper_id}")
async def delete_paper_admin(
    paper_id: uuid.UUID,
    session: SessionDep,
    _: User = Depends(require_role("admin"))
) -> Any:
    """Delete any paper from library (Admin only)."""
    stmt = select(Paper).where(Paper.id == paper_id)
    result = await session.execute(stmt)
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    try:
        from app.db.chroma import delete_paper_chunks
        delete_paper_chunks(user_id=paper.user_id, paper_id=paper.id)
    except Exception:
        pass

    if os.path.exists(paper.file_path):
        try:
            os.remove(paper.file_path)
        except Exception:
            pass
        
    await session.delete(paper)
    await session.commit()
    return {"status": "ok", "message": "Paper deleted successfully"}

@router.get("/{paper_id}", response_model=PaperResponse)
async def read_paper(
    paper_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """Get a specific paper by id (Owner or Admin)."""
    is_admin = current_user.role == UserRole.admin or getattr(current_user.role, "value", None) == "admin"
    if is_admin:
        stmt = select(Paper).where(Paper.id == paper_id)
    else:
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
    """Delete a paper. Admin can delete any paper, regular users can delete their own."""
    is_admin = current_user.role == UserRole.admin or getattr(current_user.role, "value", None) == "admin"
    if is_admin:
        stmt = select(Paper).where(Paper.id == paper_id)
    else:
        stmt = select(Paper).where(Paper.id == paper_id, Paper.user_id == current_user.id)
        
    result = await session.execute(stmt)
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    # Delete from chroma
    try:
        from app.db.chroma import delete_paper_chunks
        delete_paper_chunks(user_id=paper.user_id, paper_id=paper.id)
    except Exception:
        pass

    # Delete file from disk
    if os.path.exists(paper.file_path):
        try:
            os.remove(paper.file_path)
        except Exception:
            pass
        
    await session.delete(paper)
    await session.commit()
    return {"status": "ok", "message": "Paper deleted successfully"}
