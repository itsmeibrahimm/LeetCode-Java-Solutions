"""add payer_reference_id

Revision ID: 2f9e4fa3d729
Revises: 48d665df86d2
Create Date: 2019-12-20 23:02:06.853667

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2f9e4fa3d729"
down_revision = "48d665df86d2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payers", sa.Column("payer_reference_id", sa.Text))
    op.add_column("payers", sa.Column("payer_reference_id_type", sa.Text))
    op.create_index(
        "payers_payer_reference_id_and_type_idx",
        "payers",
        ["payer_reference_id", "payer_reference_id_type"],
    )


def downgrade():
    pass
