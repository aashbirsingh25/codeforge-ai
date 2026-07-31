import uuid
import pytest
from datetime import datetime, timezone
from app.main import app
from app.core.auth import get_current_user
from app.core.security import create_access_token
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
    Individual tests can clear or modify app.dependency_overrides as needed.
    """
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    yield
    app.dependency_overrides.pop(get_current_user, None)
