import uuid
from typing import Optional
import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.base import get_db_session
from app.db.models import User
from app.core.security import decode_access_token


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    FastAPI dependency to extract JWT access token from Authorization header,
    verify signature/expiry, and load current authenticated User object.
    """
    unauthorized_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization or not authorization.startswith("Bearer "):
        raise unauthorized_exc

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise unauthorized_exc

    try:
        payload = decode_access_token(token)
        user_id_str: Optional[str] = payload.get("sub")
        if not user_id_str:
            raise unauthorized_exc
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError, AttributeError):
        raise unauthorized_exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise unauthorized_exc

    return user
