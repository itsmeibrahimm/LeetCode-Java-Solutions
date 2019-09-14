"""update payment-intents table

Revision ID: 058c002c518a
Revises: 87ec26b0d274
Create Date: 2019-09-11 15:23:48.024738

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "058c002c518a"
down_revision = "87ec26b0d274"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payment_intents", sa.Column("metadata", sa.JSON))


def downgrade():
    pass
