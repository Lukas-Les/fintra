"""
Add salt to users table
"""

from yoyo import step

__depends__ = {"20250802_01_NML4q-add-user-id-to-transactions"}

steps = [
    step(
        """
        ALTER TABLE users
        ADD COLUMN salt VARCHAR(50) NOT NULL DEFAULT '';
        """,
        """
        ALTER TABLE users
        DROP COLUMN salt;
        """,
    )
]
