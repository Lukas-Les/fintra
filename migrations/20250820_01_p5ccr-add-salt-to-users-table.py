"""
Add salt to users table
"""

from yoyo import step

__depends__ = {"20250802_01_NML4q-add-user-id-to-transactions"}

steps = [
    step(
        """
        ALTER TABLE users
        ADD COLUMN salt BYTEA DEFAULT
            decode(
                substring(
                    md5(random()::text || clock_timestamp()::text) for 8
                ),
            'hex'
        );
        """,
        """
        ALTER TABLE users
        DROP COLUMN salt;
        """,
    ),
]
