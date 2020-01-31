"""payin payer migration tracking

Revision ID: 1bbf73e7fa89
Revises: b646b644987b
Create Date: 2020-01-30 13:23:47.904555

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Integer, Text


# revision identifiers, used by Alembic.
revision = "1bbf73e7fa89"
down_revision = "b646b644987b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "failed_consumer",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("stripe_id", Text),
        sa.Column("stripe_country_id", Integer),
    )

    op.create_table(
        "consumer_backfill_tracking",
        sa.Column("id", Integer, primary_key=True),
        sa.Column("consumer_id", Integer),
    )


def downgrade():
    pass
