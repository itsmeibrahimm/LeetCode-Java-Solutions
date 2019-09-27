"""replace varchars

Revision ID: 343158108d1c
Revises: af3d33b758e0
Create Date: 2019-09-26 16:11:59.838264

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "343158108d1c"
down_revision = "af3d33b758e0"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        table_name="cart_payments",
        column_name="client_description",
        type_=sa.types.Text,
    )

    op.alter_column(table_name="payers", column_name="payer_type", type_=sa.types.Text)
    op.alter_column(table_name="payers", column_name="dd_payer_id", type_=sa.types.Text)
    op.alter_column(table_name="payers", column_name="payer_type", type_=sa.types.Text)
    op.alter_column(table_name="payers", column_name="country", type_=sa.types.Text)
    op.alter_column(table_name="payers", column_name="description", type_=sa.types.Text)

    op.alter_column(
        table_name="payment_charges", column_name="provider", type_=sa.types.Text
    )
    op.alter_column(
        table_name="payment_charges", column_name="status", type_=sa.types.Text
    )
    op.alter_column(
        table_name="payment_charges", column_name="currency", type_=sa.types.Text
    )

    op.alter_column(
        table_name="payment_intents", column_name="capture_method", type_=sa.types.Text
    )
    op.alter_column(
        table_name="payment_intents", column_name="country", type_=sa.types.Text
    )
    op.alter_column(
        table_name="payment_intents", column_name="currency", type_=sa.types.Text
    )
    op.alter_column(
        table_name="payment_intents", column_name="status", type_=sa.types.Text
    )

    op.alter_column(
        table_name="payment_intents_adjustment_history",
        column_name="currency",
        type_=sa.types.Text,
    )

    op.alter_column(
        table_name="pgp_customers", column_name="pgp_code", type_=sa.types.Text
    )
    op.alter_column(
        table_name="pgp_customers", column_name="currency", type_=sa.types.Text
    )

    op.alter_column(
        table_name="pgp_payment_charges", column_name="provider", type_=sa.types.Text
    )
    op.alter_column(
        table_name="pgp_payment_charges", column_name="status", type_=sa.types.Text
    )
    op.alter_column(
        table_name="pgp_payment_charges", column_name="currency", type_=sa.types.Text
    )

    op.alter_column(
        table_name="pgp_payment_intents", column_name="provider", type_=sa.types.Text
    )
    op.alter_column(
        table_name="pgp_payment_intents", column_name="currency", type_=sa.types.Text
    )
    op.alter_column(
        table_name="pgp_payment_intents",
        column_name="capture_method",
        type_=sa.types.Text,
    )
    op.alter_column(
        table_name="pgp_payment_intents", column_name="status", type_=sa.types.Text
    )

    op.alter_column(
        table_name="pgp_payment_methods", column_name="pgp_code", type_=sa.types.Text
    )
    op.alter_column(
        table_name="pgp_payment_methods", column_name="pgp_card_id", type_=sa.types.Text
    )


def downgrade():
    pass
