"""create unique idempotency_key indecies

Revision ID: 09befdc4560e
Revises: 65e0ba00dfbd
Create Date: 2019-11-06 10:02:03.950080

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "09befdc4560e"
down_revision = "65e0ba00dfbd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "payment_intents_idempotency_key_unique_idx",
        "payment_intents",
        ["idempotency_key"],
    )
    op.drop_index("payment_intents_idempotency_key_idx")


def downgrade():
    pass
