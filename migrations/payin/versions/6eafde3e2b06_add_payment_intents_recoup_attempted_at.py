"""add payment_intents recoup_attempted_at

Revision ID: 6eafde3e2b06
Revises: 5633231f860a
Create Date: 2020-02-01 07:00:21.341071

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6eafde3e2b06"
down_revision = "5633231f860a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "payment_intents",
        sa.Column("recoup_attempted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    pass
