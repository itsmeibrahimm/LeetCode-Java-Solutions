"""add external_purchasecard_user_token column

Revision ID: 65856708ee2f
Revises: 16e7899664d5
Create Date: 2020-02-05 10:41:47.050100

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "65856708ee2f"
down_revision = "16e7899664d5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "auth_request",
        sa.Column("external_purchasecard_user_token", sa.Text(), nullable=False),
    )
    op.add_column("auth_request", sa.Column("current_state", sa.Text(), nullable=False))
    op.create_index(
        "auth_request_external_token_and_state_idx",
        "auth_request",
        ["external_purchasecard_user_token", "current_state"],
    )
    op.drop_index("auth_request_created_at_sorted_idx")
    op.drop_index("auth_request_state_created_at_sorted_idx")


def downgrade():
    # No need to undo index removals.
    op.drop_index("auth_request_external_token_and_state_idx")
    op.drop_column("auth_request", "external_purchasecard_user_token")
    op.drop_column("auth_request", "current_state")
