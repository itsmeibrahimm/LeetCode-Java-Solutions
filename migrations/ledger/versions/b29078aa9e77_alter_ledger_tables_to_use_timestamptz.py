"""alter ledger tables to use timestamptz

Revision ID: b29078aa9e77
Revises: 8699db6e2144
Create Date: 2019-09-25 23:54:45.223727

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b29078aa9e77"
down_revision = "8699db6e2144"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        table_name="mx_ledgers",
        column_name="created_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="mx_ledgers",
        column_name="updated_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="mx_ledgers",
        column_name="submitted_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="mx_ledgers",
        column_name="finalized_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="mx_scheduled_ledgers",
        column_name="start_time",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="mx_scheduled_ledgers",
        column_name="end_time",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="mx_scheduled_ledgers",
        column_name="created_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="mx_scheduled_ledgers",
        column_name="updated_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="mx_transactions",
        column_name="routing_key",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="mx_transactions",
        column_name="created_at",
        type_=sa.types.DateTime(timezone=True),
    )
    op.alter_column(
        table_name="mx_transactions",
        column_name="updated_at",
        type_=sa.types.DateTime(timezone=True),
    )


def downgrade():
    pass
