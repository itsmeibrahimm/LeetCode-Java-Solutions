"""create auth_request and auth_request_state tables

Revision ID: 1c476cfd86c3
Revises:
Create Date: 2019-12-03 17:38:30.520853

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "1c476cfd86c3"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auth_request",
        sa.Column(
            "id", postgresql.UUID(as_uuid=False), nullable=False, primary_key=True
        ),
        sa.Column("shift_id", sa.Text(), nullable=False),
        sa.Column("delivery_id", sa.Text(), nullable=False),
        sa.Column("dasher_id", sa.Text()),
        sa.Column("store_id", sa.Text(), nullable=False),
        sa.Column("store_city", sa.Text()),
        sa.Column("store_business_name", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
    )

    op.create_table(
        "auth_request_state",
        sa.Column(
            "id", postgresql.UUID(as_uuid=False), nullable=False, primary_key=True
        ),
        sa.Column(
            "auth_request_id",
            postgresql.UUID(as_uuid=False),
            sa.schema.ForeignKey("auth_request.id"),
            nullable=False,
        ),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("subtotal", sa.BigInteger(), nullable=False),
        sa.Column("subtotal_tax", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()
        ),
    )

    op.create_index(
        "auth_request_state_auth_request_id_fkey",
        "auth_request_state",
        ["auth_request_id"],
    )
    op.create_index("auth_request_shift_id_idx", "auth_request", ["shift_id"])
    op.create_index(
        "auth_request_delivery_id_shift_id_store_id_key",
        "auth_request",
        ["delivery_id", "shift_id", "store_id"],
        unique=True,
    )

    op.create_index(
        "auth_request_created_at_sorted_idx",
        "auth_request",
        [text("created_at ASC NULLS FIRST")],
    )

    op.create_index(
        "auth_request_state_created_at_sorted_idx",
        "auth_request_state",
        [text("created_at ASC NULLS FIRST")],
    )


def downgrade():
    # NOTE: this should really not be run at all EVER
    # op.drop_index("auth_request_state_auth_request_id_fkey")
    # op.drop_index("auth_request_shift_id_idx")
    # op.drop_index("auth_request_delivery_id_shift_id_store_id_key")
    # op.drop_index("auth_request_created_at_sorted_idx")
    # op.drop_index("auth_request_state_created_at_sorted_idx")
    #
    # op.drop_table("auth_request")
    # op.drop_table("auth_request_state")
    pass
