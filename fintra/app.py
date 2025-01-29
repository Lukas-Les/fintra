import os
import psycopg2

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/main")

async def connect_to_db():
    """Create a new database connection."""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

async def health_check(request):
    try:
        conn = await connect_to_db()
        await conn.close()
        return JSONResponse({"status": "ok", "message": "Database connected"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

routes = [
    Route("/health", endpoint=health_check)
]

app = Starlette(debug=True, routes=routes)
