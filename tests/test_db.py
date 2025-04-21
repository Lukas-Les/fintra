import json
import pytest
import time
import os

from datetime import datetime
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient


# Import your application modules
from fintra.app import app, Transaction, TransactionType
from fintra import db


@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

@pytest.fixture(autouse=True)
async def clear_database():
    """Clear the database before each test."""
    try:
        conn = await db.create_or_return_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("TRUNCATE TABLE transactions")
    except Exception as e:
        pytest.skip(f"Could not clear database: {e}")

# Test the Transaction class
class TestTransaction:
    def test_from_request_body(self):
        # Test creating a Transaction from request body
        test_data = {
            "amount": 100.50,
            "type": "income",
            "category": "salary",
            "description": "Monthly pay",
            "party": "Employer Inc.",
            "date": "2025-04-20T10:30:00"
        }

        # Convert to bytes as it would come from a request
        body_bytes = json.dumps(test_data).encode()

        # Create transaction from request body
        transaction = Transaction.from_request_body(body_bytes)

        # Verify fields
        assert transaction.amount == 100.50
        assert transaction.type == TransactionType.INCOME
        assert transaction.category == "salary"
        assert transaction.description == "Monthly pay"
        assert transaction.party == "Employer Inc."

    def test_as_dict(self):
        # Test converting Transaction to dict
        transaction = Transaction(
            amount=Decimal(75.99), # type: ignore
            type=TransactionType.EXPENSE,
            category="dining",
            description="Dinner with friends",
            party="Restaurant",
            date=datetime(2025, 4, 19, 19, 30)
        )

        result = transaction.as_dict()

        assert result["amount"] == 75.99
        assert result["type"] == "expense"
        assert result["category"] == "dining"
        assert result["description"] == "Dinner with friends"
        assert result["party"] == "Restaurant"

# Test API endpoints with real database
@pytest.mark.integration
class TestAPIWithRealDB:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        # Test health check endpoint
        response = client.get("/health")
        
        # Verify response
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["message"] == "Database connected"
    
    @pytest.mark.asyncio
    async def test_transaction_post(self, client):
        # Test data
        transaction_data = {
            "amount": 200.50,
            "type": "income",
            "category": "freelance",
            "description": "Website design",
            "party": "Client XYZ",
            "date": "2025-04-21T09:00:00"
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
