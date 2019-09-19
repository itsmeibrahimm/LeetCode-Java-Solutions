"""remove confirmation_method

Revision ID: 5442a422c00a
Revises: 2f882f4e6488
Create Date: 2019-09-18 17:59:17.026041

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "5442a422c00a"
down_revision = "2f882f4e6488"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("pgp_payment_intents", "confirmation_method")
    op.drop_column("payment_intents", "confirmation_method")


def downgrade():
    pass
