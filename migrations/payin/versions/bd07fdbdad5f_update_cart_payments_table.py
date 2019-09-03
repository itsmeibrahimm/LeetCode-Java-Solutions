"""update cart_payments table

Revision ID: bd07fdbdad5f
Revises: 0304ed952ab6
Create Date: 2019-08-29 15:24:16.861067

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "bd07fdbdad5f"
down_revision = "0304ed952ab6"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("cart_payments", "payer_id", nullable=True)


def downgrade():
    pass
