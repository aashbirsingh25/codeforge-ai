import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# Lazy/dynamic engine creation helper to support dynamic settings overrides
def get_async_engine(db_url: str | None = None) -> AsyncEngine:
    url = db_url or settings.DATABASE_URL
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    pool_cls = NullPool if is_testing else AsyncAdaptedQueuePool
    return create_async_engine(
        url,
        echo=False,
        future=True,
        poolclass=pool_cls
    )


engine = get_async_engine()

# Session factory for async database sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency helper to yield async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
