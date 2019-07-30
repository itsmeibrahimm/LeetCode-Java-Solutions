"""create payers table

Revision ID: ed65fbc0a6a9
Revises:
Create Date: 2019-07-24 16:17:29.341954

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ed65fbc0a6a9"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payer",
        sa.Column("id", sa.String(255), nullable=False, primary_key=True),
        sa.Column("payer_type", sa.String(32), nullable=False),
        sa.Column("dd_payer_id", sa.String(128)),
        sa.Column("legacy_stripe_customer_id", sa.Text()),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("account_balance", sa.BigInteger),
        sa.Column("description", sa.String(64)),
        sa.Column("metadata", sa.JSON()),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column("deleted_at", sa.DateTime()),
    )


def downgrade():
    pass
