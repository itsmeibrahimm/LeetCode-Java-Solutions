"""update payment_intents table

Revision ID: 2f882f4e6488
Revises: 058c002c518a
Create Date: 2019-09-17 15:12:16.784615

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2f882f4e6488"
down_revision = "058c002c518a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payment_intents", sa.Column("legacy_consumer_charge_id", sa.Integer))


def downgrade():
    pass
