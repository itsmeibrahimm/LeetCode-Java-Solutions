"""create payment_charges table

Revision ID: 9c6de1143d93
Revises: d3457e3562fe
Create Date: 2019-08-18 13:23:33.458246

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "9c6de1143d93"
down_revision = "d3457e3562fe"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_charges",
        sa.Column(
            "id", postgresql.UUID(as_uuid=False), nullable=False, primary_key=True
        ),
        sa.Column(
            "payment_intent_id",
            postgresql.UUID(as_uuid=True),
            sa.schema.ForeignKey("payment_intents.id"),
            nullable=False,
        ),
        sa.Column("legacy_id", sa.Text),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.Text, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("amount_refunded", sa.Integer),
        sa.Column("application_fee_amount", sa.Integer),
        sa.Column("payout_account_id", sa.Text),
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
