"""add server default for payer_type

Revision ID: 8dbe8a1914f0
Revises: 2f9e4fa3d729
Create Date: 2019-12-23 17:13:30.324051

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "8dbe8a1914f0"
down_revision = "2f9e4fa3d729"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        table_name="payers", column_name="payer_type", server_default="marketplace"
    )


def downgrade():
    pass
