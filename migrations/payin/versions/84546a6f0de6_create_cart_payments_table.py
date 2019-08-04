"""create cart_payments table

Revision ID: 84546a6f0de6
Revises: ca09cb90118d
Create Date: 2019-07-29 16:43:23.545580

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "84546a6f0de6"
down_revision = "ca09cb90118d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cart_payments",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True
        ),
        sa.Column(
            "payer_id",
            sa.String(255),
            sa.schema.ForeignKey("payers.id"),
            nullable=False,
        ),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("reference_id", sa.BigInteger),
        sa.Column("reference_ct_id", sa.BigInteger),
        sa.Column("legacy_charge_id", sa.BigInteger),
        sa.Column("legacy_consumer_id", sa.BigInteger),
        sa.Column("amount_original", sa.Integer, nullable=False),
        sa.Column("amount_total", sa.Integer, nullable=False),
        sa.Column("client_description", sa.String(128)),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column("deleted_at", sa.DateTime()),
    )


def downgrade():
    pass
