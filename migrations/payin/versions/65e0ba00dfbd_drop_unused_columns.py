"""drop unused columns

Revision ID: 65e0ba00dfbd
Revises: b13155ae0be3
Create Date: 2019-11-01 00:23:34.053115

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "65e0ba00dfbd"
down_revision = "b13155ae0be3"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("payers", "account_balance")
    op.drop_column("pgp_customers", "account_balance")
    op.drop_column("pgp_payment_intents", "provider")


def downgrade():
    pass
