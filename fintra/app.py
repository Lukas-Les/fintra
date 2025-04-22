import enum
import json

from typing import Any

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.types import Double
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.routing import Route
from starlette.schemas import SchemaGenerator

from fintra import db


schemas = SchemaGenerator(
    {"openapi": "3.0.0", "info": {"title": "Example API", "version": "1.0"}}
)


class TransactionType(enum.Enum):
    EXPENSE = "expense"
    INCOME = "income"


@dataclass
class Transaction:
    amount: Double
    type: TransactionType
    category: str
    description: str
    party: str
    date: datetime

    @classmethod
    def from_request_body(cls, body: bytes):
        body_json = json.loads(body.decode())
        if body_json.get("type") == "expense":
            _type = TransactionType.EXPENSE
        else:
            _type = TransactionType.INCOME
        return cls(
            amount=body_json.get("amount"),
            type=_type,
            category=body_json.get("category"),
            description=body_json.get("description"),
            party=body_json.get("party"),
            date=body_json.get("date") or datetime.now(),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "type": self.type.value,
            "category": self.category,
            "description": self.description,
            "party": self.party,
            "date": self.date,
        }


async def health_check(request: Request):
    conn = await db.create_or_return_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT 1;")
        result = await cursor.fetchone()  # Fetch to ensure the query works

        return JSONResponse(
            {"status": "ok", "message": "Database connected", "result": result}
        )


async def transaction(request: Request) -> JSONResponse:
    transaction = Transaction.from_request_body(await request.body())
    if request.method == "POST":
        conn = await db.create_or_return_connection()
        async with conn.cursor() as cursor:
            query = """
                INSERT INTO transactions (amount, type, category, description, party, date)
                VALUES (%(amount)s, %(type)s, %(category)s, %(description)s, %(party)s, %(date)s);
            """
            await cursor.execute(query, params=transaction.as_dict())
            response_obj = {"result": "transaction pushed"}
        return JSONResponse(content=json.dumps(response_obj))
    else:
        response_obj = {"result": "only post implemented"}
        return JSONResponse(content=json.dumps(response_obj))


def openapi_schema(request):
    return schemas.OpenAPIResponse(request=request)


routes = [
    Route("/health", endpoint=health_check, methods=["GET"]),
    Route("/docs", endpoint=openapi_schema, methods=["GET"]),
    Route("/transaction", endpoint=transaction, methods=["POST"]),
]

app = Starlette(debug=True, routes=routes)
