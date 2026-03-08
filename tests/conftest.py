"""Shared pytest fixtures for backend tests."""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import get_db


# ── Event loop ────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── IDs ───────────────────────────────────────────────────────────

CLINIC_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
USER_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


# ── Mock DB session ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def mock_db() -> AsyncMock:
    """Provide a mock AsyncSession for unit tests."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    return session


# ── Test HTTP client with dependency overrides ───────────────────


class _FakeAuthMiddleware(BaseHTTPMiddleware):
    """Replace TenantJWTMiddleware: inject tenant state from constructor args."""

    def __init__(self, app, *, clinic_id: str, user_id: str, role: str):
        super().__init__(app)
        self._clinic_id = clinic_id
        self._user_id = user_id
        self._role = role

    async def dispatch(self, request: Request, call_next):
        request.state.clinic_id = self._clinic_id
        request.state.user_id = self._user_id
        request.state.user_role = self._role
        return await call_next(request)


def _mock_db_override() -> AsyncGenerator[AsyncMock, None]:
    async def _gen():
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        session.execute = AsyncMock()
        yield session
    return _gen()


def _make_test_app(role: str = "provider", *, inject_auth: bool = True) -> FastAPI:
    """Create a lightweight FastAPI app WITHOUT TenantJWTMiddleware.

    If ``inject_auth`` is True, a fake middleware injects tenant/user state
    so that RBAC + tenant dependencies resolve normally.
    If False, no state is set (simulates missing auth).
    """
    app = FastAPI(title="test")

    if inject_auth:
        app.add_middleware(
            _FakeAuthMiddleware,
            clinic_id=str(CLINIC_ID),
            user_id=str(USER_ID),
            role=role,
        )

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.dependency_overrides[get_db] = _mock_db_override
    return app


@pytest_asyncio.fixture
async def client_provider() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client that hits the app as a 'provider' role."""
    app = _make_test_app("provider")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def client_admin() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client that hits the app as an 'admin' role."""
    app = _make_test_app("admin")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def client_viewer() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client that hits the app as a 'viewer' role (read-only)."""
    app = _make_test_app("viewer")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def client_no_auth() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with no auth state (simulates missing token)."""
    app = _make_test_app(inject_auth=False)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
