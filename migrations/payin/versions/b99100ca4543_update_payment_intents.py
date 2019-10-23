"""update payment_intents

Revision ID: b99100ca4543
Revises: 317b376f9aac
Create Date: 2019-10-22 16:11:55.359641

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "b99100ca4543"
down_revision = "317b376f9aac"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("payment_intents", "amount_received")
    op.drop_column("payment_intents", "amount_capturable")


def downgrade():
    pass
