import json

from datetime import datetime
from decimal import Decimal

from fintra.app import Transaction, TransactionType


class TestTransaction:
    def test_from_request_body(self):
        test_data = {
            "amount": 100.50,
            "type": "income",
            "category": "salary",
            "description": "Monthly pay",
            "party": "Employer Inc.",
            "date": "2025-04-20T10:30:00",
        }

        body_bytes = json.dumps(test_data).encode()

        transaction = Transaction.from_request_body(body_bytes)

        assert transaction.amount == 100.50
        assert transaction.type == TransactionType.INCOME
        assert transaction.category == "salary"
        assert transaction.description == "Monthly pay"
        assert transaction.party == "Employer Inc."

    def test_as_dict(self):
        transaction = Transaction(
            amount=Decimal(75.99),  # type: ignore
            type=TransactionType.EXPENSE,
            category="dining",
            description="Dinner with friends",
            party="Restaurant",
            date=datetime(2025, 4, 19, 19, 30),
        )

        result = transaction.as_dict()

        assert result["amount"] == 75.99
        assert result["type"] == "expense"
        assert result["category"] == "dining"
        assert result["description"] == "Dinner with friends"
        assert result["party"] == "Restaurant"
