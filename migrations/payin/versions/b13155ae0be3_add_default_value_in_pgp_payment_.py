"""add default value in pgp_payment_intents table

Revision ID: b13155ae0be3
Revises: 3e9ea485cae5
Create Date: 2019-10-31 16:10:22.035574

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b13155ae0be3"
down_revision = "3e9ea485cae5"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        table_name="pgp_payment_intents",
        column_name="provider",
        server_default="stripe",
    )
    op.add_column("pgp_customers", sa.Column("balance", sa.BigInteger))


def downgrade():
    pass
