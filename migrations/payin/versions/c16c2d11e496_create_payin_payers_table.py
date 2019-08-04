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
        sa.Column("legacy_id", sa.BigInteger),
        sa.Column("pgp_code", sa.String(16)),
        sa.Column("pgp_resource_id", sa.Text(), nullable=False),
        sa.Column(
            "payer_id",
            sa.String(255),
            sa.schema.ForeignKey("payers.id"),
            nullable=False,
        ),
        sa.Column("account_balance", sa.BigInteger),
        sa.Column("currency", sa.String(16)),
        sa.Column("default_payment_method_id", sa.Text()),
        sa.Column("legacy_default_source_id", sa.Text()),
        sa.Column("legacy_default_card_id", sa.Text()),
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
