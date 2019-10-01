"""update pgp_customers for multiple customer support

Revision ID: 19297d35efaa
Revises: e43fe3718038
Create Date: 2019-10-01 00:16:32.141435

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "19297d35efaa"
down_revision = "e43fe3718038"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pgp_customers", sa.Column("country", sa.types.Text))
    op.add_column("pgp_customers", sa.Column("is_primary", sa.types.Boolean))


def downgrade():
    pass
