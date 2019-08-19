"""add closed_at in mx_scheduled_ledgers table

Revision ID: 8699db6e2144
Revises: 2dc625a67b61
Create Date: 2019-08-16 11:30:21.210069

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8699db6e2144"
down_revision = "2dc625a67b61"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "mx_scheduled_ledgers",
        sa.Column(
            "closed_at",
            sa.BigInteger,
            server_default=sa.schema.DefaultClause("0"),
            nullable=False,
        ),
    )
    op.drop_constraint(
        "uq_mx_scheduled_ledgers_payment_account_id_start_time_end_time",
        "mx_scheduled_ledgers",
    )
    op.create_unique_constraint(
        "uq_mx_scheduled_ledgers_ledger_uniqueness",
        "mx_scheduled_ledgers",
        ["payment_account_id", "start_time", "end_time", "closed_at"],
    )


def downgrade():
    pass
