"""update delete_payer_requests table

Revision ID: a328fb338f9b
Revises: 8dbe8a1914f0
Create Date: 2019-12-27 10:44:09.574979

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "a328fb338f9b"
down_revision = "8dbe8a1914f0"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("delete_payer_requests_request_id_idx")
    op.alter_column(
        "delete_payer_requests", "request_id", new_column_name="client_request_id"
    )
    op.create_unique_constraint(
        "delete_payer_requests_client_request_id_unique_idx",
        "delete_payer_requests",
        ["client_request_id"],
    )


def downgrade():
    pass
