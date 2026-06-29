from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, CurrentUser, require_role
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()

# Admin only endpoints
@router.get("/", response_model=list[UserResponse])
async def read_users(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(require_role("admin"))
) -> Any:
    """Retrieve users (Admin only)."""
    stmt = select(User).offset(skip).limit(limit)
    result = await session.execute(stmt)
    users = result.scalars().all()
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: uuid.UUID,
    session: SessionDep,
    _: User = Depends(require_role("admin"))
) -> Any:
    """Get a specific user by id (Admin only)."""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    session: SessionDep,
    _: User = Depends(require_role("admin"))
) -> Any:
    """Update a user (Admin only)."""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data:
        from app.core.security import get_password_hash
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["password_hash"] = hashed_password
        
    for field, value in update_data.items():
        setattr(user, field, value)
        
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

@router.delete("/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    _: User = Depends(require_role("admin"))
) -> Any:
    """Delete a user (Admin only)."""
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Users cannot delete themselves")
        
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    await session.delete(user)
    await session.commit()
    return {"status": "ok"}
