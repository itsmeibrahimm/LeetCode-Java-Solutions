"""remove CartPayment.legacy_consumer_id

Revision ID: 2c78044f67da
Revises: ffe22b33f903
Create Date: 2019-09-25 15:52:45.343917

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "2c78044f67da"
down_revision = "ffe22b33f903"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("cart_payments", "legacy_charge_id")


def downgrade():
    pass
