import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.main import app
from app.core.auth import get_current_user
from app.core.security import create_access_token
from app.db.base import AsyncSessionLocal, engine, get_db_session
from app.db.models import User

# Standard test user ID and model instance
TEST_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TEST_USER = User(
    id=TEST_USER_ID,
    email="testuser@codeforge.ai",
    hashed_password="$2b$12$test_hashed_password_example",
    created_at=datetime.now(timezone.utc)
)

# Valid JWT bearer token for testing
TEST_AUTH_TOKEN = create_access_token(str(TEST_USER_ID))
TEST_AUTH_HEADERS = {"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}


@pytest.fixture(autouse=True)
def override_auth_dependency():
    """
    Autouse fixture that overrides the get_current_user dependency
    to return TEST_USER for API test suites.
    """
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture(autouse=True)
async def seed_test_user_and_clean_engine():
    """
    Autouse function-scoped fixture that seeds TEST_USER and disposes engine pool after each test.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == TEST_USER_ID))
        existing_user = result.scalars().first()
        if not existing_user:
            user = User(
                id=TEST_USER_ID,
                email="testuser@codeforge.ai",
                hashed_password="$2b$12$test_hashed_password_example",
                created_at=datetime.now(timezone.utc)
            )
            session.add(user)
            await session.commit()
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    """
    Provides a fresh AsyncSession for tests and overrides get_db_session.
    """
    async with AsyncSessionLocal() as session:
        async def _get_test_db():
            yield session

        app.dependency_overrides[get_db_session] = _get_test_db
        try:
            yield session
        finally:
            app.dependency_overrides.pop(get_db_session, None)
