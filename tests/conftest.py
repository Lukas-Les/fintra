import sys
import os
import asyncio
import pytest_asyncio

from asgi_lifespan import LifespanManager
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv(dotenv_path="./.env.test")

from fintra.app import app  # noqa: E402
from fintra import db  # noqa: E402


@pytest_asyncio.fixture(scope="session")
async def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    conn = await db.create_or_return_connection()

    async with conn.cursor() as cursor:
        await cursor.execute("DELETE FROM transactions;")
        await cursor.execute("DELETE FROM users;")
    yield


@pytest_asyncio.fixture()
async def async_client():
    """Create a properly configured async client."""
    async with LifespanManager(app):
        async with AsyncClient(
            base_url="http://test", transport=ASGITransport(app)
        ) as client:
            yield client


@pytest_asyncio.fixture()
async def authenticated_client(async_client: AsyncClient):
    """Provides an authenticated TestClient instance."""
    user_email = "test@example.com"
    user_password = "password123"

    # Create user
    await async_client.post("/create-user", data={"email": user_email, "password": user_password})

    # Login to get the access token cookie
    response = await async_client.post(
        "/login", data={"email": user_email, "password": user_password}
    )
    assert response.status_code == 303
    assert "access_token" in async_client.cookies

    return async_client, user_email
