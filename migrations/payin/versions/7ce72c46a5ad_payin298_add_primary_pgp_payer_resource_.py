"""payin298 add primary_pgp_payer_resource_id

Revision ID: 7ce72c46a5ad
Revises: 17db52d02b0e
Create Date: 2020-01-08 23:27:40.262397

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy.dialects import postgresql

revision = "7ce72c46a5ad"
down_revision = "17db52d02b0e"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        table_name="payers",
        column_name="legacy_default_dd_stripe_card_id",
        type_=sa.BigInteger,
    )
    op.add_column(
        "payers", sa.Column("primary_pgp_payer_resource_id", sa.Text, nullable=True)
    )
    op.add_column(
        "payers",
        sa.Column("primary_pgp_payer_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("payers", sa.Column("primary_pgp_code", sa.Text, nullable=True))


def downgrade():
    pass
