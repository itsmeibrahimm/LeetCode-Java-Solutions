"""update pgp_refunds table

Revision ID: 2b21dd93bd58
Revises: 7c71a70c37b2
Create Date: 2019-11-27 14:49:31.823235

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2b21dd93bd58"
down_revision = "7c71a70c37b2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pgp_refunds", sa.Column("pgp_charge_resource_id", sa.Text, nullable=True)
    )


def downgrade():
    pass
