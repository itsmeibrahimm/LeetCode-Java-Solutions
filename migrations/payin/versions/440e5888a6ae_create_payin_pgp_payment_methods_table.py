"""create payin_pgp_payment_methods table

Revision ID: 440e5888a6ae
Revises: 6b871ea27e4a
Create Date: 2019-08-04 16:51:24.768071

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy.dialects import postgresql

revision = "440e5888a6ae"
down_revision = "6b871ea27e4a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pgp_payment_methods",
        sa.Column(
            "id", postgresql.UUID(as_uuid=False), nullable=False, primary_key=True
        ),
        sa.Column("pgp_code", sa.String(16)),
        sa.Column("pgp_resource_id", sa.Text(), nullable=False),
        sa.Column("payer_id", postgresql.UUID(as_uuid=False)),
        sa.Column("pgp_card_id", sa.String(255)),
        sa.Column("legacy_consumer_id", sa.Text()),
        sa.Column("object", sa.Text()),
        sa.Column("type", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("attached_at", sa.DateTime()),
        sa.Column("detached_at", sa.DateTime()),
    )


def downgrade():
    pass
