"""create transactions table

Revision ID: 2e948ab7bd04
Revises: 
Create Date: 2025-04-20 08:05:30.020205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e948ab7bd04'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("transactions", 
        sa.Column( "id", sa.INTEGER, primary_key=True),
        sa.Column("amount", sa.NUMERIC(precision=10, scale=2), nullable=False),
        sa.Column("type", sa.Enum("income", "expense", name="transaction_type", create_type=True), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("party", sa.String(100), nullable=True),
        sa.Column("date", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("transactions")
    op.execute("DROP TYPE transaction_type")
