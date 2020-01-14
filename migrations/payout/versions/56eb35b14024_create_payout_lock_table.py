"""create payout_lock table

Revision ID: 56eb35b14024
Revises:
Create Date: 2020-01-13 15:47:01.422296

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "56eb35b14024"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("payout_lock", sa.Column("lock_id", sa.Text, primary_key=True))


def downgrade():
    pass
