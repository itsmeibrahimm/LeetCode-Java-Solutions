"""update index in paymentintents for capture query optimization

Revision ID: 24a37ccea734
Revises: 65e0ba00dfbd
Create Date: 2019-11-06 11:18:18.355064

"""
from alembic import op


# revision identifiers, used by Alembic.
from sqlalchemy import text

revision = "24a37ccea734"
down_revision = "09befdc4560e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "payment_intents_status_created_at_capture_after_idx",
        "payment_intents",
        [
            "status",
            text("created_at DESC"),
            text("capture_after DESC"),  # default nulls first
        ],
    )


def downgrade():
    op.drop_index("payment_intents_status_created_at_capture_after_idx")
