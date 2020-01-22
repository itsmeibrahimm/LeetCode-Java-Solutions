"""update payout table

Revision ID: 2bd360ad864e
Revises: 56eb35b14024
Create Date: 2020-01-21 16:08:45.834664

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2bd360ad864e"
down_revision = "56eb35b14024"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payout_lock", sa.Column("status", sa.Text))
    op.add_column(
        "payout_lock",
        sa.Column(
            "lock_timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
        ),
    )
    op.add_column("payout_lock", sa.Column("ttl_sec", sa.Integer))


def downgrade():
    pass
