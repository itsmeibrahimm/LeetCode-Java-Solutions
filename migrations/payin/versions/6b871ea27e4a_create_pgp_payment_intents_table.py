"""create pgp_payment_intents table

Revision ID: 6b871ea27e4a
Revises: 84546a6f0de6
Create Date: 2019-07-30 12:25:10.474405

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "6b871ea27e4a"
down_revision = "a1c2febf294e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pgp_payment_intents",
        sa.Column(
            "id", postgresql.UUID(as_uuid=False), nullable=False, primary_key=True
        ),
        sa.Column(
            "payment_intent_id",
            postgresql.UUID(as_uuid=True),
            sa.schema.ForeignKey("payment_intents.id"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.Text, nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("resource_id", sa.Text),
        sa.Column("invoice_resource_id", sa.Text),
        sa.Column("charge_resource_id", sa.Text),
        sa.Column("payment_method_resource_id", sa.Text, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("amount_capturable", sa.Integer),
        sa.Column("amount_received", sa.Integer),
        sa.Column("application_fee_amount", sa.Integer),
        sa.Column("capture_method", sa.String(32), nullable=False),
        sa.Column("confirmation_method", sa.String(32), nullable=False),
        sa.Column("payout_account_id", sa.Text),
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
