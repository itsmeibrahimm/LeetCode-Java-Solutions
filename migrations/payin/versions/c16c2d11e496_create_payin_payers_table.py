"""create payin_payers table

Revision ID: c16c2d11e496
Revises:
Create Date: 2019-08-02 20:26:31.599899

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c16c2d11e496"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payers",
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
