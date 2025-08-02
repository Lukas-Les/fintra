"""
add_user_id_to_transactions
"""

from yoyo import step

__depends__ = {"20250730_01_oxheC-create-users-table"}

steps = [
    step(
        """
        ALTER TABLE transactions
        ADD COLUMN user_id INTEGER NOT NULL;

        ALTER TABLE transactions
        ADD CONSTRAINT fk_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE;
        """,
        """
        ALTER TABLE transactions
        DROP CONSTRAINT fk_user;

        ALTER TABLE transactions
        DROP COLUMN user_id;
        """,
    )
]
