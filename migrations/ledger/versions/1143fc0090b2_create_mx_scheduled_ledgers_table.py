"""create mx_scheduled_ledgers table

Revision ID: 1143fc0090b2
Revises: c164900a6620
Create Date: 2019-08-01 11:52:22.320037

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "1143fc0090b2"
down_revision = "c164900a6620"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mx_scheduled_ledgers",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True
        ),
        sa.Column("payment_account_id", sa.String(255), nullable=False),
        sa.Column(
            "ledger_id",
            postgresql.UUID(as_uuid=True),
            sa.schema.ForeignKey("mx_ledgers.id"),
            nullable=False,
        ),
        sa.Column("interval_type", sa.String(32), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
    )
    op.create_unique_constraint(
        "uq_mx_scheduled_ledgers_payment_account_id_start_time_end_time",
        "mx_scheduled_ledgers",
        ["payment_account_id", "start_time", "end_time"],
    )


def downgrade():
    pass
