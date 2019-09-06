"""create payment_intents_adjustment_history table

Revision ID: d3457e3562fe
Revises: 440e5888a6ae
Create Date: 2019-08-16 17:49:40.394228

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d3457e3562fe"
down_revision = "440e5888a6ae"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_intents_adjustment_history",
        sa.Column(
            "id", postgresql.UUID(as_uuid=False), nullable=False, primary_key=True
        ),
        sa.Column(
            "payer_id",
            postgresql.UUID(as_uuid=True),
            sa.schema.ForeignKey("payers.id"),
            nullable=False,
        ),
        sa.Column(
            "payment_intent_id",
            postgresql.UUID(as_uuid=True),
            sa.schema.ForeignKey("payment_intents.id"),
            nullable=False,
        ),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("amount_original", sa.Integer, nullable=False),
        sa.Column("amount_delta", sa.Integer, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
    )


def downgrade():
    pass
