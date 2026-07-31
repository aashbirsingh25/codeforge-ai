import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.base import get_db_session
from app.db.models import User
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters long")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str

    class Config:
        from_attributes = True


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/signup", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    req: SignupRequest,
    db: AsyncSession = Depends(get_db_session)
) -> Any:
    """Register a new user account and return an access token."""
    # Check if user with given email already exists
    result = await db.execute(select(User).where(User.email == req.email.strip().lower()))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists."
        )

    # Hash password and create new user row
    hashed_pw = hash_password(req.password)
    user = User(
        email=req.email.strip().lower(),
        hashed_password=hashed_pw
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate JWT token
    access_token = create_access_token(user_id=str(user.id))

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    req: LoginRequest,
    db: AsyncSession = Depends(get_db_session)
) -> Any:
    """Authenticate user credentials and return an access token."""
    result = await db.execute(select(User).where(User.email == req.email.strip().lower()))
    user = result.scalars().first()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    access_token = create_access_token(user_id=str(user.id))

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )
