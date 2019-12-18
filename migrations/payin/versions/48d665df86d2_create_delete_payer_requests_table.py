"""create delete_payer_requests table

Revision ID: 48d665df86d2
Revises: b8854a24ee17
Create Date: 2019-12-18 12:16:02.665855

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "48d665df86d2"
down_revision = "b8854a24ee17"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "delete_payer_requests",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True
        ),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consumer_id", sa.Integer),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True)),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("summary", sa.JSON),
        sa.Column("retry_count", sa.Integer, nullable=False),
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
        sa.Column("acknowledged", sa.Boolean, nullable=False),
    )

    op.create_index(
        "delete_payer_requests_request_id_idx", "delete_payer_requests", ["request_id"]
    )

    op.create_index(
        "delete_payer_requests_status_idx",
        "delete_payer_requests",
        ["status"],
        postgresql_where=sa.text("status = 'IN PROGRESS'"),
    )


def downgrade():
    pass
