"""update pgp_payment_intents table

Revision ID: 0fedcefc2893
Revises: bd07fdbdad5f
Create Date: 2019-08-30 10:14:11.143908

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0fedcefc2893"
down_revision = "bd07fdbdad5f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "pgp_payment_intents", sa.Column("customer_resource_id", sa.Text, nullable=True)
    )


def downgrade():
    pass
