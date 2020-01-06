"""alter pgp_customers.legacy_id to legacy_dd_stripe_customer_id

Revision ID: b3cad933c7e3
Revises: a328fb338f9b
Create Date: 2020-01-02 14:23:22.649453

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b3cad933c7e3"
down_revision = "a328fb338f9b"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("pgp_customers", "legacy_id")
    op.add_column("payers", sa.Column("legacy_dd_stripe_customer_id", sa.BigInteger))


def downgrade():
    pass
