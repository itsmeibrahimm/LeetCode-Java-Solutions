"""create pgp_payment_charges table

Revision ID: f47a4d690309
Revises: 9c6de1143d93
Create Date: 2019-08-18 14:00:39.519222

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "f47a4d690309"
down_revision = "9c6de1143d93"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pgp_payment_charges",
        sa.Column(
            "id", postgresql.UUID(as_uuid=False), nullable=False, primary_key=True
        ),
        sa.Column(
            "payment_charge_id",
            postgresql.UUID(as_uuid=True),
            sa.schema.ForeignKey("payment_charges.id"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.Text, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("amount_refunded", sa.Integer),
        sa.Column("application_fee_amount", sa.Integer),
        sa.Column("payout_account_id", sa.Text),
        sa.Column("resource_id", sa.Text),
        sa.Column("intent_resource_id", sa.Text),
        sa.Column("invoice_resource_id", sa.Text),
        sa.Column("payment_method_resource_id", sa.Text, nullable=False),
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
