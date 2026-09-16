import copy
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import AuthenticatedUser, get_current_user, get_current_user_optional
from app.database import Base, get_db
from app.main import app

# A single shared in-memory SQLite connection for the whole test run.
# Plain sqlite:///:memory: gives every new connection its own empty
# database, which breaks as soon as a request opens a second connection.
# StaticPool keeps them all on one connection so state persists across
# requests within a test.
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def _clean_database() -> Iterator[None]:
    Base.metadata.create_all(_engine)
    yield
    Base.metadata.drop_all(_engine)


@pytest.fixture(autouse=True)
def _background_session_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    # Feedback email delivery runs in a BackgroundTask, after the
    # request-scoped session from get_db is closed, so it opens its own from
    # the app-wide factory. Point that at the test database too, or the task
    # writes to whatever DATABASE_URL happens to be configured.
    monkeypatch.setattr("app.routers.feedback.SessionLocal", _TestingSessionLocal)


def _override_get_db() -> Iterator:
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(id="user-1", email="user1@example.com")


@pytest.fixture
def db_session() -> Iterator[Session]:
    """A session for tests that need to set up or inspect DB state directly
    (e.g. backdating a row's timestamp), separate from the session the app
    uses to serve requests. Shares the same StaticPool connection, so
    commits made here are visible to the app's own session."""
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(current_user: AuthenticatedUser) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: current_user
    # get_current_user_optional never goes through get_current_user's
    # override (it calls the real function directly to fall back to
    # anonymous on failure), so it needs its own override to default tests
    # to "signed in as current_user" the same way the rest of the fixture
    # does. A test that needs an anonymous viewer overrides this locally.
    app.dependency_overrides[get_current_user_optional] = lambda: current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


_VALID_COURSE = {
    "id": "test-course",
    "title": "Test Course",
    "units": [
        {
            "id": "u1",
            "title": "Unit One",
            "lessons": [
                {
                    "id": "l1",
                    "title": "Lesson One",
                    "writtenLesson": {
                        "id": "w1",
                        "title": "Overview",
                        "markdown": "# hi",
                    },
                    "codePractices": [
                        {
                            "type": "function",
                            "id": "cp1",
                            "title": "Add",
                            "functionSignature": "add(a, b)",
                            "description": "Add two numbers.",
                            "testSuite": [{"input": [1, 2], "expectedOutput": 3}],
                        }
                    ],
                    "interactivePractices": [
                        {
                            "id": "ip1",
                            "title": "Practice",
                            "activities": [
                                {
                                    "type": "multipleChoice",
                                    "id": "a1",
                                    "question": "2 + 2?",
                                    "options": ["3", "4"],
                                    "correctIndex": 1,
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    ],
}


@pytest.fixture
def sample_course() -> dict:
    return copy.deepcopy(_VALID_COURSE)
