"""Shared test fixtures for TrendTracker backend tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — ensure all models are registered on Base.metadata
from app.collectors.google_mock import GoogleMockCollector
from app.collectors.registry import registry
from app.collectors.weibo_mock import WeiboMockCollector
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def use_mock_collector():
    """Replace real collectors with mocks for all tests (no network I/O)."""
    registry.register(WeiboMockCollector)
    registry.register(GoogleMockCollector)
    yield
    # Restore real collectors after each test
    from app.collectors.google import GoogleTrendsCollector
    from app.collectors.weibo import WeiboCollector

    registry.register(WeiboCollector)
    registry.register(GoogleTrendsCollector)


@pytest.fixture
async def db_session():
    """Provide a fresh SQLite in-memory database session for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_client(db_session: AsyncSession):
    """Async HTTP test client with DB dependency overridden to use SQLite."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
