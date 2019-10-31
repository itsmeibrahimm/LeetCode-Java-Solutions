"""update column in payers and pgp_payment_intents

Revision ID: 3e9ea485cae5
Revises: 4be76f96fe33
Create Date: 2019-10-31 14:29:18.863118

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3e9ea485cae5"
down_revision = "4be76f96fe33"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payers", sa.Column("balance", sa.BigInteger))
    op.add_column(
        "pgp_payment_intents",
        sa.Column("pgp_code", sa.Text, server_default="stripe", nullable=False),
    )


def downgrade():
    op.drop_column("payers", "balance")
    op.drop_column("pgp_payment_intents", "pgp_code")
