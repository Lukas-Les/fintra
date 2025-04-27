import pytest

from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient

from fintra import app, db


@pytest.fixture
def client():
    return TestClient(app.app)


@pytest.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app.app), base_url="http://testserver"
    ) as client:
        yield client


@pytest.mark.integration
class TestAPIWithRealDB:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        # Test health check endpoint
        response = client.get("/health")

        # Verify response
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_transaction_post(self, client):
        # Test data
        transaction_data = {
            "amount": 200.50,
            "type": "income",
            "category": "freelance",
            "description": "Website design",
            "party": "Client XYZ",
            "date": "2025-04-21T09:00:00",
        }

        # Make the POST request
        response = client.post("/transaction", json=transaction_data)

        # Verify response
        assert response.status_code == 200

        # Verify data was actually inserted in the database
        conn = await db.create_or_return_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM transactions WHERE amount = 200.50")
            result = await cursor.fetchone()
            assert result is not None
            assert float(result[1]) == 200.50  # amount, convert to float for comparison
            assert result[3] == "freelance"  # category
