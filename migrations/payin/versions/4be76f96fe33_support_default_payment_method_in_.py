"""support default payment method in payers table

Revision ID: 4be76f96fe33
Revises: b99100ca4543
Create Date: 2019-10-22 21:40:47.774996

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "4be76f96fe33"
down_revision = "b99100ca4543"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "payers",
        sa.Column(
            "default_payment_method_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
    )
    op.add_column(
        "payers",
        sa.Column("legacy_default_dd_stripe_card_id", sa.Integer, nullable=True),
    )


def downgrade():
    pass
