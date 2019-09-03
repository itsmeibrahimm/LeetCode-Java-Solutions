"""update payment_intents_adjustment_history table

Revision ID: ea8de59e4c4e
Revises: 0fedcefc2893
Create Date: 2019-08-30 17:37:37.472187

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "ea8de59e4c4e"
down_revision = "0fedcefc2893"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("payment_intents_adjustment_history", "payer_id", nullable=True)


def downgrade():
    pass
