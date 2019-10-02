"""create pgp_refunds table

Revision ID: 75738c1938f2
Revises: ff11e712444e
Create Date: 2019-09-20 17:02:46.834050

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "75738c1938f2"
down_revision = "ff11e712444e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pgp_refunds",
        sa.Column(
            "id", postgresql.UUID(as_uuid=False), nullable=False, primary_key=True
        ),
        sa.Column("refund_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.Text),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("pgp_code", sa.Text),
        sa.Column("pgp_resource_id", sa.Text),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("reason", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.current_timestamp(),
        ),
    )
    op.create_index("pgp_refunds_refund_id_idx", "pgp_refunds", ["refund_id"])


def downgrade():
    pass
