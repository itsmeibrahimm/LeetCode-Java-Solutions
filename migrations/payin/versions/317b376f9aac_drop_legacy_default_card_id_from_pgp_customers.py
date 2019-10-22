"""drop legacy_default_card_id from pgp_customers table

Revision ID: 317b376f9aac
Revises: 75738c1938f2
Create Date: 2019-10-21 11:40:06.676194

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "317b376f9aac"
down_revision = "75738c1938f2"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("pgp_customers", "legacy_default_card_id")


def downgrade():
    op.add_column("pgp_customers", sa.Column("legacy_default_card_id", sa.Text()))
