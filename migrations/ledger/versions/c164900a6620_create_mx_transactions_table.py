"""create mx_transactions table

Revision ID: c164900a6620
Revises: 63280ebef894
Create Date: 2019-08-01 11:44:52.163102

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "c164900a6620"
down_revision = "63280ebef894"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mx_transactions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True
        ),
        sa.Column("payment_account_id", sa.String(255), nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("currency", sa.String(6), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column(
            "ledger_id",
            postgresql.UUID(as_uuid=True),
            sa.schema.ForeignKey("mx_ledgers.id"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("routing_key", sa.DateTime(), nullable=False),
        sa.Column("target_id", sa.String(255)),
        sa.Column("legacy_transaction_id", sa.String(255)),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column("context", sa.JSON),
        sa.Column("metadata", sa.JSON),
    )
    op.create_index(
        "idx_mx_transactions_payment_account_id_idempotency_key_uq",
        "mx_transactions",
        ["payment_account_id", "idempotency_key"],
        unique=True,
    )


def downgrade():
    pass
