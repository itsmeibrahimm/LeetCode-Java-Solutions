"""create ledger mx_ledgers table

Revision ID: 63280ebef894
Revises:
Create Date: 2019-08-01 11:01:59.640192

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "63280ebef894"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mx_ledgers",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True
        ),
        sa.Column("payment_account_id", sa.String(255), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("balance", sa.BigInteger, nullable=False),
        sa.Column("amount_paid", sa.BigInteger),
        sa.Column("currency", sa.String(6), nullable=False),
        sa.Column("created_by_employee_id", sa.String(255)),
        sa.Column("submitted_by_employee_id", sa.String(255)),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("rolled_to_ledger_id", postgresql.UUID(as_uuid=True)),
        sa.Column("legacy_transfer_id", sa.String(255)),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column("submitted_at", sa.DateTime()),
        sa.Column("finalized_at", sa.DateTime()),
    )


def downgrade():
    pass
