"""create payment_intents table

Revision ID: a1c2febf294e
Revises: 84546a6f0de6
Create Date: 2019-07-30 11:16:04.206826

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a1c2febf294e"
down_revision = "84546a6f0de6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_intents",
        sa.Column(
            "id", postgresql.UUID(as_uuid=False), nullable=False, primary_key=True
        ),
        sa.Column(
            "cart_payment_id",
            postgresql.UUID(as_uuid=True),
            sa.schema.ForeignKey("cart_payments.id"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.Text),
        sa.Column("amount_initiated", sa.Integer, nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("amount_capturable", sa.Integer),
        sa.Column("amount_received", sa.Integer),
        sa.Column("application_fee_amount", sa.Integer),
        sa.Column("capture_method", sa.String(32), nullable=False),
        sa.Column("confirmation_method", sa.String(32), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("statement_descriptor", sa.Text),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column("captured_at", sa.DateTime()),
        sa.Column("cancelled_at", sa.DateTime()),
    )


def downgrade():
    pass
