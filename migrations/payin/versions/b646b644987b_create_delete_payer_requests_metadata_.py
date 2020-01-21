"""create delete_payer_requests_metadata table

Revision ID: b646b644987b
Revises: 7ce72c46a5ad
Create Date: 2020-01-20 11:44:19.603872

Its a temp table. It should be deleted by 2020-01-31 after
fix for deleting multiple stripe accounts with same email.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy.dialects import postgresql

revision = "b646b644987b"
down_revision = "7ce72c46a5ad"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "delete_payer_requests_metadata",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False, primary_key=True
        ),
        sa.Column("client_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consumer_id", sa.BigInteger, nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
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

    op.create_unique_constraint(
        "delete_payer_requests_metadata_client_request_id_unique_idx",
        "delete_payer_requests_metadata",
        ["client_request_id"],
    )

    op.create_index(
        "delete_payer_requests_metadata_in_progress_status_idx",
        "delete_payer_requests_metadata",
        ["status"],
        postgresql_where=sa.text("status = 'IN PROGRESS'"),
    )


def downgrade():
    pass
