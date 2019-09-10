"""update cart_payments table

Revision ID: 03d7b19e2410
Revises: ea8de59e4c4e
Create Date: 2019-09-04 09:31:16.472331

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "03d7b19e2410"
down_revision = "ea8de59e4c4e"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("cart_payments", "reference_id")
    op.drop_column("cart_payments", "reference_ct_id")
    op.add_column("cart_payments", sa.Column("reference_id", sa.Text))
    op.add_column("cart_payments", sa.Column("reference_type", sa.Text))
    op.add_column("cart_payments", sa.Column("legacy_stripe_card_id", sa.Integer))
    op.add_column("cart_payments", sa.Column("legacy_provider_customer_id", sa.Text))
    op.add_column(
        "cart_payments", sa.Column("legacy_provider_payment_method_id", sa.Text)
    )
    op.add_column("cart_payments", sa.Column("legacy_provider_card_id", sa.Text))


def downgrade():
    pass
