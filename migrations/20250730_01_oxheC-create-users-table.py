"""
create users table
"""

from yoyo import step

__depends__ = {"20250712_01_Siyn7-create-transactions-table"}

steps = [
    step(
        """
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) DEFAULT 'user',
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            updated_at TIMESTAMP NOT NULL DEFAULT current_timestamp
        );
        """,
        """
        DROP TABLE users;
        """,
    )
]
