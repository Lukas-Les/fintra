import os

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import psycopg
from psycopg.rows import TupleRow

from psycopg import AsyncConnection, AsyncCursor

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:pass@localhost:5432/main"
)

# TODO: implement a connection pool
_connection: AsyncConnection | None = None


async def _create_connection() -> psycopg.AsyncConnection:
    """Create a new async database connection."""
    return await psycopg.AsyncConnection.connect(DATABASE_URL, autocommit=True)


async def create_or_return_connection() -> psycopg.AsyncConnection:
    global _connection
    if _connection is None or _connection.closed:
        _connection = await _create_connection()
    return _connection 


@asynccontextmanager
async def connect_with_lock(lock_key: int) -> AsyncGenerator[AsyncCursor[TupleRow], None]:
    conn = await create_or_return_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT pg_try_advisory_lock(%s::bigint)", (lock_key, ))
        try:
            yield cursor
        finally:
            await cursor.execute("SELECT pg_advisory_unlock(%s::bigint)", (lock_key, ))
