"""
Pytest configuration and fixtures for testing.
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.main import app
from src.core.database import Base, get_db


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
)

test_async_session = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_async_session() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database session override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_order_data() -> dict:
    """Sample order data for testing."""
    return {
        "symbol": "EUR_USD",
        "side": "buy",
        "order_type": "market",
        "size": "10000",
        "stop_loss": "1.0850",
        "leverage": 10,
    }


@pytest.fixture
def sample_account_data() -> dict:
    """Sample account data for testing."""
    return {
        "account_id": "test-account-123",
        "balance": "10000.00",
        "equity": "10250.00",
        "margin_used": "1000.00",
        "margin_available": "9250.00",
        "unrealized_pnl": "250.00",
        "realized_pnl_today": "0.00",
        "currency": "USD",
        "leverage": 20,
    }
