"""
create transactions table
"""

from yoyo import step

__depends__ = {}

steps = [
    step(
        """
        CREATE TYPE transaction_type AS ENUM ('income', 'expense');
        """,
        """
        DROP TYPE transaction_type;
        """
    ),
    step(
        """
        CREATE TABLE transactions (
            id SERIAL PRIMARY KEY,
            amount NUMERIC(10, 2) NOT NULL,
            type transaction_type NOT NULL,
            category VARCHAR(50),
            description VARCHAR(200),
            party VARCHAR(100),
            date TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
        """,
        """
        DROP TABLE transactions;
        """
    )
]
