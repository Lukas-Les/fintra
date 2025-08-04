import pytest

from httpx import AsyncClient
from datetime import datetime


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Tests if the health check endpoint is working."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.text == "hello there"


@pytest.mark.asyncio
async def test_create_user_success(async_client: AsyncClient, setup_database: None):
    """Tests successful user creation."""
    response = await async_client.post(
        "/create-user",
        data={"email": "testuser@example.com", "password": "a-secure-password"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "testuser@example.com"
    assert "access_token" in response.cookies
    assert response.headers["hx-redirect"] == "/"


@pytest.mark.asyncio
async def test_create_user_already_exists(async_client: AsyncClient):
    """Tests that creating a user with an existing email fails."""
    await async_client.post(
        "/create-user",
        data={"email": "existing@example.com", "password": "password123"},
    )
    with pytest.raises(ValueError):
        await async_client.post(
            "/create-user",
            data={"email": "existing@example.com", "password": "anotherpassword"},
        )


@pytest.mark.asyncio
async def test_create_user_invalid_email(async_client: AsyncClient):
    """Tests user creation with an invalid email format."""
    with pytest.raises(ValueError):
        await async_client.post(
            "/create-user", data={"email": "not-an-email", "password": "password123"}
        )


@pytest.mark.asyncio
async def test_create_user_short_password(async_client: AsyncClient):
    """Tests user creation with a password that is too short."""
    with pytest.raises(ValueError):
        await async_client.post(
            "/create-user", data={"email": "user@example.com", "password": "123"}
        )


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    """Tests successful login for an existing user."""
    email = "loginuser@example.com"
    password = "password123"
    await async_client.post("/create-user", data={"email": email, "password": password})
    # Now, log in
    response = await async_client.post(
        "/login", data={"email": email, "password": password}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Login successful"
    assert "access_token" in response.cookies
    assert response.headers["hx-redirect"] == "/"


@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient):
    """Tests login with an incorrect password."""
    email = "wrongpass@example.com"
    password = "password123"
    await async_client.post("/create-user", data={"email": email, "password": password})
    with pytest.raises(ValueError):
        await async_client.post(
            "/login", data={"email": email, "password": "wrongpassword"}
        )


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client: AsyncClient):
    """Tests login for a user that does not exist."""
    with pytest.raises(Exception):
        await async_client.post(
            "/login", data={"email": "nouser@example.com", "password": "password"}
        )


# Transaction and Balance tests
@pytest.mark.asyncio
async def test_transaction_unauthenticated(async_client: AsyncClient):
    """Tests that an unauthenticated user cannot create a transaction."""
    transaction_data = {
        "amount": 100.50,
        "type": "income",
        "category": "Salary",
        "description": "Monthly pay",
        "party": "Work",
        "date": datetime.now().isoformat(),
    }
    response = await async_client.post("/transaction", json=transaction_data)
    assert response.status_code == 403  # Forbidden


@pytest.mark.asyncio
async def test_balance_unauthenticated(async_client: AsyncClient):
    """Tests that an unauthenticated user cannot view their balance."""
    response = await async_client.get("/balance")
    assert response.status_code == 403  # Forbidden


@pytest.mark.asyncio
async def test_transaction_and_balance_authenticated(authenticated_client):
    """Tests creating transactions and then checking the balance for an authenticated user."""
    client, user_email = authenticated_client

    # Post an income transaction
    income_data = {
        "amount": 1500.00,
        "type": "income",
        "category": "Salary",
        "description": "Paycheck",
        "party": "Employer",
        "date": datetime.now().isoformat(),
    }
    response = await client.post("/transaction", json=income_data)
    assert response.status_code == 201

    # Post an expense transaction
    expense_data = {
        "amount": 75.50,
        "type": "expense",
        "category": "Groceries",
        "description": "Weekly shopping",
        "party": "Supermarket",
        "date": datetime.now().isoformat(),
    }
    response = await client.post("/transaction", json=expense_data)
    assert response.status_code == 201

    # Check the balance
    response = await client.get("/balance")
    assert response.status_code == 200
    data = response.json()
    assert "balance" in data
    assert pytest.approx(data["balance"]) == 1500.00 - 75.50


@pytest.mark.asyncio
async def test_balance_no_transactions(authenticated_client):
    """Tests that the balance is 0 if a user has no transactions."""
    client, user_email = authenticated_client
    response = await client.get("/balance")
    assert response.status_code == 200
    data = response.json()
    assert "balance" in data
    assert data["balance"] == 0.0
