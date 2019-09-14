"""update cart_payments table

Revision ID: 87ec26b0d274
Revises: 03d7b19e2410
Create Date: 2019-09-11 15:21:03.039575

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "87ec26b0d274"
down_revision = "03d7b19e2410"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("cart_payments", "type")
    op.add_column("cart_payments", sa.Column("metadata", sa.JSON))


def downgrade():
    pass
