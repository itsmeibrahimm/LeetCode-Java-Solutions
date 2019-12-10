"""drop unused indices for pi table

Revision ID: e348f0ad9c00
Revises: 677609c7cb01
Create Date: 2019-12-10 12:54:18.188664

"""
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = "e348f0ad9c00"
down_revision = "677609c7cb01"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("payment_intents_status_updated_at_idx")
    op.drop_index("payment_intents_status_capture_after_idx")


def downgrade():
    op.create_index(
        "payment_intents_status_capture_after_idx",
        "payment_intents",
        ["status", text("capture_after ASC NULLS FIRST")],
    )
    op.create_index(
        "payment_intents_status_updated_at_idx",
        "payment_intents",
        ["status", text("updated_at DESC NULLS LAST")],
    )
