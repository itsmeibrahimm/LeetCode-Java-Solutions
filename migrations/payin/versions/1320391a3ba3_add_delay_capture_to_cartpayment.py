"""add delay_capture to CartPayment

Revision ID: 1320391a3ba3
Revises: 84bdedfad53a
Create Date: 2019-08-30 13:41:31.955506

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1320391a3ba3"
down_revision = "84bdedfad53a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("cart_payments", sa.Column("delay_capture", sa.Boolean))


def downgrade():
    op.drop_column("cart_payments", "delay_capture")
