import os
import pytest
import sys

from fintra import db

# Add the project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


TEST_DB_URL = "postgresql://testuser:testpass@localhost:2222/test_db"


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Set up the test database configuration"""
    os.environ["DATABASE_URL"] = TEST_DB_URL

    # Run Alembic migrations directly - assumes you've already set up your test database
    # Comment this out if you want to run migrations manually
    import subprocess
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    yield


@pytest.fixture(autouse=True)
async def clear_database():
    """Clear the database before each test."""
    try:
        conn = await db.create_or_return_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("TRUNCATE TABLE transactions")
    except Exception as e:
        pytest.skip(f"Could not clear database: {e}")
