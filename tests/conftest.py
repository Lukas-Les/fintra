import os
import pytest
import sys

from fintra import config
from fintra import db

# Add the project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(autouse=True)
async def clear_database():
    """Clear the database before each test."""
    try:
        conn = await db.create_or_return_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("TRUNCATE TABLE transactions")
    except Exception as e:
        pytest.skip(f"Could not clear database: {e}")
