import enum
import json
import logging

import functools

from typing import Any, Awaitable, Callable, cast, TypeVar

from dataclasses import dataclass
from datetime import datetime

from prometheus_client import start_http_server, Summary
from sqlalchemy.types import Double
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.requests import Request
from starlette.routing import Route
from starlette.schemas import SchemaGenerator

from fintra import db


REQUEST_TIME = Summary(
    "request_processing_seconds", "Request processing duratino", ["endpoint"]
)


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

        if not (amount := body_json.get("amount")):
            raise ValueError("Can't submit transaction withount amount")

        if not (type_str := body_json.get("type")):
            raise ValueError("Can't submit transaction withount type")

        if type_str == "expense":
            _type = TransactionType.EXPENSE
        elif type_str == "income":
            _type = TransactionType.INCOME
        else:
            raise ValueError("Type must be one of ['income', 'expense']")

        return cls(
            amount=amount,
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


T = TypeVar("T", bound=Callable[..., Awaitable[Any]])


def async_timed(endpoint_name: str) -> Callable[[T], T]:
    def decorator(func: T) -> T:
        @functools.wraps(func)
        async def wrapped(*args, **kwargs) -> Any:
            with REQUEST_TIME.labels(endpoint_name=endpoint_name).time():
                return await func(*args, **kwargs)

        return cast(T, wrapped)

    return decorator


@async_timed("health")
async def health_check(request: Request):
    conn = await db.create_or_return_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT 1;")
        await cursor.fetchone()

        return Response()


@async_timed("transaction")
async def transaction(request: Request) -> Response:
    transaction = Transaction.from_request_body(await request.body())
    if request.method == "POST":
        conn = await db.create_or_return_connection()
        async with conn.cursor() as cursor:
            query = """
                INSERT INTO transactions (amount, type, category, description, party, date)
                VALUES (%(amount)s, %(type)s, %(category)s, %(description)s, %(party)s, %(date)s);
            """
            await cursor.execute(query, params=transaction.as_dict())
        return Response()
    else:
        response_obj = {"error": "GET is not implemeted for this path"}
        return JSONResponse(content=json.dumps(response_obj), status_code=404)


@async_timed("balance")
async def balance(request: Request) -> JSONResponse | Response:
    if request.method == "GET":
        conn = await db.create_or_return_connection()
        async with conn.cursor() as cursor:
            query = """
                SELECT
                    SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) -
                    SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS balance
                FROM transactions;
            """
            await cursor.execute(query)
            if not (row := await cursor.fetchone()):
                return Response(status_code=500)
            balance = row[0]
            return JSONResponse({"balance": float(balance)})
    return JSONResponse(content={}, status_code=404)


def openapi_schema(request):
    return schemas.OpenAPIResponse(request=request)


routes = [
    Route("/health", endpoint=health_check, methods=["GET"]),
    Route("/docs", endpoint=openapi_schema, methods=["GET"]),
    Route("/transaction", endpoint=transaction, methods=["POST"]),
    Route("/balance", endpoint=balance, methods=["GET"]),
]

app = Starlette(debug=True, routes=routes)
metrics_app = start_http_server(port=8001)
