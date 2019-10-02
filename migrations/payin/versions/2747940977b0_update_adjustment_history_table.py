"""update adjustment history table

Revision ID: 2747940977b0
Revises: 5442a422c00a
Create Date: 2019-09-20 10:19:25.775664

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2747940977b0"
down_revision = "19297d35efaa"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "payment_intents_adjustment_history", sa.Column("idempotency_key", sa.Text)
    )
    op.create_unique_constraint(
        "payment_intents_adjustment_history_idempotency_key_unique_idx",
        "payment_intents_adjustment_history",
        ["idempotency_key"],
    )


def downgrade():
    pass
