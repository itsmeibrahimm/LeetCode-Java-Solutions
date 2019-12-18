"""add index cart_payments table

Revision ID: b8854a24ee17
Revises: e348f0ad9c00
Create Date: 2019-12-17 16:19:57.602071

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "b8854a24ee17"
down_revision = "e348f0ad9c00"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "cart_payments_legacy_consumer_id_idx", "cart_payments", ["legacy_consumer_id"]
    )


def downgrade():
    pass
