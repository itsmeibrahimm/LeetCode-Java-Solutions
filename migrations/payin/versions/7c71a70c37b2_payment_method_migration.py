"""payment_method_migration

Revision ID: 7c71a70c37b2
Revises: 24a37ccea734
Create Date: 2019-11-20 16:46:50.940441

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "7c71a70c37b2"
down_revision = "24a37ccea734"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(table_name="payment_methods", column_name="payer_id", nullable=True)
    op.drop_constraint(
        constraint_name="payment_methods_payer_id_fkey",
        table_name="payment_methods",
        type_="foreignkey",
    )
    op.drop_constraint(
        constraint_name="payment_intents_payment_method_id_fkey",
        table_name="payment_intents",
        type_="foreignkey",
    )
    op.create_index(
        "pgp_payment_methods_payment_method_id_idx",
        "pgp_payment_methods",
        ["payment_method_id"],
    )


def downgrade():
    pass
