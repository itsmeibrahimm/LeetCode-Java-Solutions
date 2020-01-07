"""drop dd_payer_id and payer_type

Revision ID: 17db52d02b0e
Revises: b3cad933c7e3
Create Date: 2020-01-07 00:53:04.413264

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "17db52d02b0e"
down_revision = "b3cad933c7e3"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("payers", "payer_type")
    op.drop_column("payers", "dd_payer_id")


def downgrade():
    pass
