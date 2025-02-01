import os
import psycopg

from psycopg.rows import dict_row
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/main")

async def connect_to_db() -> psycopg.AsyncConnection:
    """Create a new async database connection."""
    return await psycopg.AsyncConnection.connect(DATABASE_URL)

async def health_check(request):
    try:
        async with await connect_to_db() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute("SELECT 1;")
                result = await cur.fetchone()  # Fetch to ensure the query works

        return JSONResponse({"status": "ok", "message": "Database connected", "result": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

routes = [
    Route("/health", endpoint=health_check)
]

app = Starlette(debug=True, routes=routes)
