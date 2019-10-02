"""create refunds table

Revision ID: ff11e712444e
Revises: 2747940977b0
Create Date: 2019-09-20 17:02:31.775883

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "ff11e712444e"
down_revision = "2747940977b0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "refunds",
        sa.Column(
            "id", postgresql.UUID(as_uuid=False), nullable=False, primary_key=True
        ),
        sa.Column("payment_intent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.Text),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("reason", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
        ),
    )
    op.create_unique_constraint(
        "refunds_idempotency_key_unique_idx", "refunds", ["idempotency_key"]
    )


def downgrade():
    pass
