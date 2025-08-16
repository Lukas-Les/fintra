import os
import re
import enum
import json

import functools

from typing import Any, Awaitable, Callable, ParamSpec, cast, TypeVar
from dataclasses import dataclass
from datetime import datetime, timedelta

from argon2 import PasswordHasher
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
from starlette.datastructures import FormData
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.requests import Request
from starlette.routing import Route

from fintra import db


REQUEST_TIME = Summary(
    "request_processing_seconds", "Request processing duratino", ["endpoint"]
)


SECRET_KEY = "random"
ALGORITHM = "HS256"
SALT = os.environ["SALT"].encode()
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Token valid for 60 minutes
EMAIL_PATTERN = re.compile(r"^[\w.-]+@([\w-]+\.)+[\w-]{2,}$")

ph = PasswordHasher()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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

    @staticmethod
    def _raise_if_not_string(value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("expected type str, got" + type(value).__name__)
        return value

    @classmethod
    def from_form_data(cls, form_data: FormData):
        amount_str = cls._raise_if_not_string(form_data.get("amount"))
        if not amount_str:
            raise ValueError("can't submit transaction without amount")
        try:
            amount = float(amount_str)
        except ValueError:
            raise ValueError("amount must be a valid number")

        type_str = cls._raise_if_not_string(form_data.get("type"))
        if not type_str:
            raise ValueError("Can't submit transaction without type")
        if type_str == "expense":
            _type = TransactionType.EXPENSE
        elif type_str == "income":
            _type = TransactionType.INCOME
        else:
            raise ValueError("Type must be one of ['income', 'expense']")

        category = cls._raise_if_not_string(form_data.get("category"))
        description = cls._raise_if_not_string(form_data.get("description"))
        party = cls._raise_if_not_string(form_data.get("party"))

        if raw_date := form_data.get("date"):
            _date = datetime.fromisoformat(cls._raise_if_not_string(raw_date))
        else:
            _date = datetime.now()

        return cls(
            amount=amount,
            type=_type,
            category=category,
            description=description,
            party=party,
            date=_date,
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


P = ParamSpec("P")
R = TypeVar("R")
FuncType = Callable[P, Awaitable[R]]


def async_timed(endpoint: str) -> Callable[[FuncType], FuncType]:
    def decorator(func: FuncType) -> FuncType:
        @functools.wraps(func)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> object:
            with REQUEST_TIME.labels(endpoint=endpoint).time():
                return await func(*args, **kwargs)

        return cast(FuncType, wrapped)

    return decorator


@async_timed("health")
async def health_check(request: Request):
    conn = await db.create_or_return_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT 1;")
        await cursor.fetchone()

        return Response("hello there")


@async_timed("create-user")
async def create_user(request: Request) -> RedirectResponse:
    form = await request.form()
    if not (email := form.get("email")):
        raise ValueError("no email provided")
    if not isinstance(email, str):
        raise ValueError("email must be a text input")
    if not EMAIL_PATTERN.search(str(email)):
        raise ValueError("email is in wrong format")
    password = str(form.get("password", ""))
    if len(password) < 5:
        raise ValueError("password is too short")
    hashed = ph.hash(password=password, salt=SALT)
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
        await cursor.execute(query=query, params={"email": email, "password": hashed})
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production if using HTTPS
        max_age=int(access_token_expires.total_seconds()),
        path="/",
    )
    response.set_cookie(key="email", value=email, secure=False, path="/")
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
            result = await cursor.fetchone()
            if not result:
                return
        return AuthCredentials(["authenticated"]), SimpleUser(email)


@async_timed("login")
async def login(request: Request) -> RedirectResponse:
    form = await request.form()
    password = form.get("password")
    if not isinstance(password, str):
        raise ValueError("password must be a text entry")
    if not (email := form.get("email")):
        raise ValueError("no email provided")
    if not isinstance(email, str):
        raise ValueError("email must be a text entry")
    if not EMAIL_PATTERN.search(str(email)):
        raise ValueError("email is in wrong format")

    conn = await db.create_or_return_connection()
    async with conn.cursor() as cursor:
        query = """
            SELECT password FROM users
            WHERE email = %(email)s;
        """
        await cursor.execute(query, params={"email": email})
        result = await cursor.fetchone()
        if not result:
            raise Exception("user does not exist")
        hashed = result[0]
        ph.verify(hashed, password=password)
        if not ph.check_needs_rehash(hashed):
            new_hash = ph.hash(password=password, salt=SALT)
            query = """
                UPDATE users
                SET
                    password = %(password)s
                WHERE email = %(email)s;

            """
            await cursor.execute(
                query=query, params={"email": email, "password": new_hash}
            )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="email", value=email, secure=False, path="/")
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production if using HTTPS
        max_age=int(access_token_expires.total_seconds()),
        path="/",
    )
    return response


@async_timed("logout")
async def logout(request: Request) -> RedirectResponse:
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="email")
    return response


@async_timed("transaction")
@requires("authenticated")
async def transaction(request: Request) -> Response:
    transaction = Transaction.from_request_body(await request.body())
    conn = await db.create_or_return_connection()
    async with conn.cursor() as cursor:
        query = """
            INSERT INTO transactions (amount, type, category, description, party, date, user_id)
            SELECT %(amount)s, %(type)s, %(category)s, %(description)s, %(party)s, %(date)s, users.id
            FROM users
            WHERE users.email = %(email)s
        """
        params = transaction.as_dict()
        params["email"] = request.user.username
        await cursor.execute(query, params=params)
    return Response(status_code=201)


@async_timed("balance")
@requires("authenticated")
async def balance(request: Request) -> JSONResponse | Response:
    conn = await db.create_or_return_connection()
    async with conn.cursor() as cursor:
        query = """
            SELECT
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) -
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS balance
            FROM transactions
            JOIN users on transactions.user_id = users.id
            WHERE users.email = %(email)s;
        """
        await cursor.execute(query, params={"email": request.user.username})
        if not (row := await cursor.fetchone()):
            return Response(status_code=500)
        balance = row[0]
        if balance is None:
            balance = 0.0
        return JSONResponse({"balance": float(balance)})
    return JSONResponse(content={}, status_code=404)


middleware = [Middleware(AuthenticationMiddleware, backend=TokenAuthBackend())]

routes = [
    Route("/health", endpoint=health_check, methods=["GET"]),
    Route("/transaction", endpoint=transaction, methods=["POST"]),
    Route("/balance", endpoint=balance, methods=["GET"]),
    Route("/login", endpoint=login, methods=["POST"]),
    Route("/create-user", create_user, methods=["POST"]),
    Route("/logout", logout, methods=["POST"]),
]


app = Starlette(routes=routes, middleware=middleware)
metrics_app = start_http_server(port=8001)
