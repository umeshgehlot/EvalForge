# Environment variables must be set before any app import so pydantic-settings
# picks them up at module load time.
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET", "test-secret-for-pytest-not-real")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_async_session
from app.models import *  # noqa: F401,F403 — registers all models with Base.metadata


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    SessionMaker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionMaker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    SessionMaker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_session():
        async with SessionMaker() as session:
            yield session

    app.dependency_overrides[get_async_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
