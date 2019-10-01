"""Add payment_methods

Revision ID: e43fe3718038
Revises: 343158108d1c
Create Date: 2019-09-30 16:41:32.448176

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy.dialects import postgresql

revision = "e43fe3718038"
down_revision = "343158108d1c"
branch_labels = None
depends_on = None


def upgrade():
    # create payment_methods table
    op.create_table(
        "payment_methods",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True
        ),
        sa.Column(
            "payer_id",
            postgresql.UUID(as_uuid=True),
            sa.schema.ForeignKey("payers.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
    )
    op.add_column(
        "pgp_payment_methods",
        sa.Column("payment_method_id", postgresql.UUID(as_uuid=True)),
    )


def downgrade():
    pass
