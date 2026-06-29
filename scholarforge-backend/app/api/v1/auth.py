from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from pydantic import BaseModel

from app.api.deps import SessionDep, CurrentUser
from app.core import security
from app.core.config import settings
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(session: SessionDep, user_in: UserCreate) -> Any:
    """Register a new user."""
    stmt = select(User).where(User.email == user_in.email)
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = User(
        email=user_in.email,
        password_hash=security.get_password_hash(user_in.password),
        name=user_in.name,
        role=user_in.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

@router.post("/login", response_model=Token)
async def login(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests."""
    stmt = select(User).where(User.email == form_data.username)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, role=user.role, expires_delta=access_token_expires
        ),
        "refresh_token": security.create_refresh_token(
            user.id, role=user.role
        ),
        "token_type": "bearer",
    }

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=Token)
async def refresh_token(session: SessionDep, req: RefreshTokenRequest) -> Any:
    try:
        payload = security.jwt.decode(
            req.refresh_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid token")
            
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return {
            "access_token": security.create_access_token(
                user.id, role=user.role, expires_delta=access_token_expires
            ),
            "refresh_token": security.create_refresh_token(
                user.id, role=user.role
            ),
            "token_type": "bearer",
        }
    except Exception:
        raise HTTPException(status_code=403, detail="Could not validate credentials")

@router.get("/me", response_model=UserResponse)
async def read_user_me(current_user: CurrentUser) -> Any:
    """Get current user."""
    return current_user
