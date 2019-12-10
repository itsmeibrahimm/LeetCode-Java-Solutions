"""add-index-for-charge-id-in-payment-intents

Revision ID: 677609c7cb01
Revises: 2b21dd93bd58
Create Date: 2019-12-10 11:09:21.606816

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "677609c7cb01"
down_revision = "2b21dd93bd58"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "payment_intents_legacy_consumer_charge_id_idx",
        "payment_intents",
        ["legacy_consumer_charge_id"],
    )


def downgrade():
    pass
