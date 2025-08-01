import re
import base64
import binascii
import enum
import json
import logging

import functools

from typing import Any, Awaitable, Callable, cast, TypeVar

from dataclasses import dataclass
from datetime import datetime, timedelta

from jose import jwt, exceptions
from prometheus_client import start_http_server, Summary
from starlette.applications import Starlette
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
    requires,
)
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
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

# Configuration for JWT
SECRET_KEY = "random"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Token valid for 60 minutes
EMAIL_PATTERN = re.compile(r"^[\w.-]+@([\w-]+\.)+[\w-]{2,}$")

# Dummy user database (REPLACE WITH REAL DATABASE LOOKUP AND PASSWORD HASHING)
# Example: Store hashed passwords like 'testuser': '$2b$12$...'
DUMMY_USERS_DB = {
    "user@test.com": "pass",  # In production, this would be a hashed password
    "lukas@gmail.com": "pass",
}


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except exceptions.JWTError:
        return None


class TransactionType(enum.Enum):
    EXPENSE = "expense"
    INCOME = "income"


@dataclass
class Transaction:
    amount: float
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


def async_timed(endpoint: str) -> Callable[[T], T]:
    def decorator(func: T) -> T:
        @functools.wraps(func)
        async def wrapped(*args, **kwargs) -> Any:
            with REQUEST_TIME.labels(endpoint=endpoint).time():
                return await func(*args, **kwargs)

        return cast(T, wrapped)

    return decorator


@async_timed("health")
async def health_check(request: Request):
    conn = await db.create_or_return_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT 1;")
        await cursor.fetchone()

        return Response("hello there")


@async_timed("create-user")
async def create_user(request: Request):
    form = await request.form()
    if not (email := form.get("email")):
        raise ValueError("no email provided")
    if not EMAIL_PATTERN.search(str(email)):
        raise ValueError("email is in wrong format")
    password = str(form.get("password", ""))
    if len(password) < 5:
        raise ValueError("password is too short")

    conn = await db.create_or_return_connection()
    async with conn.cursor() as cursor:
        query = """
            SELECT email FROM users
            WHERE email = %(email)s;
        """
        await cursor.execute(query, params={"email": email})
        if await cursor.fetchone():
            raise ValueError("email already exists")
        query = """
            INSERT INTO users (email, password)
            VALUES (%(email)s, %(password)s);
        """
        await cursor.execute(query=query, params={"email": email, "password": password})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )

    response = JSONResponse({"email": email}, status_code=201)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production if using HTTPS
        max_age=int(access_token_expires.total_seconds()),
        path="/",
    )
    response.headers["HX-Redirect"] = "/"  # Example: redirect to dashboard after login
    return response

class TokenAuthBackend(AuthenticationBackend):
    async def authenticate(self, conn):
        # Check for 'access_token' cookie
        token = conn.cookies.get("access_token")
        if not token:
            return

        payload = decode_access_token(token)
        if payload is None:
            raise AuthenticationError("Invalid or expired token")

        email = payload.get("sub")
        if not email:
            return

        conn = await db.create_or_return_connection()
        async with conn.cursor() as cursor:
            query = """
                SELECT email FROM users
                WHERE email = %(email)s;
            """
            await cursor.execute(query, params={"email": email})
            result  = await cursor.fetchone()
            if not result:
                return
        return AuthCredentials(["authenticated"]), SimpleUser(email)


@async_timed("login")
async def login(request: Request) -> JSONResponse:
    form = await request.form()
    email = form.get("email")
    password = form.get("password")
    if not (email := form.get("email")):
        raise ValueError("no email provided")
    if not EMAIL_PATTERN.search(str(email)):
        raise ValueError("email is in wrong format")

    conn = await db.create_or_return_connection()
    async with conn.cursor() as cursor:
        query = """
            SELECT password FROM users
            WHERE email = %(email)s;
        """
        await cursor.execute(query, params={"email": email})
        result  = await cursor.fetchone()
        if not result:
            raise Exception("user does not exist")
    if password != result[0]:
        raise ValueError("password not correct")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )

    response = JSONResponse({"message": "Login successful", "email": email})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production if using HTTPS
        max_age=int(access_token_expires.total_seconds()),
        path="/",
    )
    response.headers["HX-Redirect"] = "/"
    return response


@async_timed("transaction")
@requires("authenticated")
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
@requires("authenticated")
async def balance(request: Request) -> JSONResponse | Response:
    email = request.user.username
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
        if balance is None:
            balance = 0.0
        return JSONResponse({"balance": float(balance)})
    return JSONResponse(content={}, status_code=404)


def openapi_schema(request):
    return schemas.OpenAPIResponse(request=request)


middleware = [Middleware(AuthenticationMiddleware, backend=TokenAuthBackend())]

routes = [
    Route("/health", endpoint=health_check, methods=["GET"]),
    Route("/docs", endpoint=openapi_schema, methods=["GET"]),
    Route("/transaction", endpoint=transaction, methods=["POST"]),
    Route("/balance", endpoint=balance, methods=["GET"]),
    Route("/login", endpoint=login, methods=["POST"]),
    Route("/create-user", create_user, methods=["POST"])
]


app = Starlette(routes=routes, middleware=middleware)
metrics_app = start_http_server(port=8001)
