"""create timestamp index

Revision ID: 2dc625a67b61
Revises: 1143fc0090b2
Create Date: 2019-08-01 16:55:46.923841

"""
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = "2dc625a67b61"
down_revision = "1143fc0090b2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "idx_mx_scheduled_ledgers_ts_inverse",
        "mx_scheduled_ledgers",
        [text("payment_account_id, start_time, end_time DESC")],
    )


def downgrade():
    pass
