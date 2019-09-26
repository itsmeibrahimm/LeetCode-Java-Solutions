"""alter payin tables to use timestamptz

Revision ID: af3d33b758e0
Revises: 2c78044f67da
Create Date: 2019-09-25 16:44:54.442997

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "af3d33b758e0"
down_revision = "2c78044f67da"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        table_name="payers",
        column_name="created_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="payers",
        column_name="updated_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="payers",
        column_name="deleted_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_payment_intents",
        column_name="created_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_payment_intents",
        column_name="updated_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_payment_intents",
        column_name="captured_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_payment_intents",
        column_name="cancelled_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_payment_charges",
        column_name="created_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_payment_charges",
        column_name="updated_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_payment_charges",
        column_name="captured_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_payment_charges",
        column_name="cancelled_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="payment_intents",
        column_name="created_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="payment_intents",
        column_name="updated_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="payment_intents",
        column_name="captured_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="payment_intents",
        column_name="cancelled_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="payment_intents_adjustment_history",
        column_name="created_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="payment_charges",
        column_name="created_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="payment_charges",
        column_name="updated_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="payment_charges",
        column_name="captured_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="payment_charges",
        column_name="cancelled_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_customers",
        column_name="created_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_customers",
        column_name="updated_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_customers",
        column_name="deleted_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="cart_payments",
        column_name="created_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="cart_payments",
        column_name="updated_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="cart_payments",
        column_name="deleted_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_payment_methods",
        column_name="created_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_payment_methods",
        column_name="updated_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_payment_methods",
        column_name="deleted_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_payment_methods",
        column_name="attached_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="pgp_payment_methods",
        column_name="detached_at",
        type_=sa.types.DateTime(timezone=True),
    )


def downgrade():
    pass
