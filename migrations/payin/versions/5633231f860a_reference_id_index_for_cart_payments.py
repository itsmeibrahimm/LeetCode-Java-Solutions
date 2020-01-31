"""reference id index for cart payments

Revision ID: 5633231f860a
Revises: 1bbf73e7fa89
Create Date: 2020-01-31 13:11:31.919826

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "5633231f860a"
down_revision = "1bbf73e7fa89"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "cart_payments_reference_type_and_id_idx",
        "cart_payments",
        ["reference_type", "reference_id"],
    )


def downgrade():
    pass
