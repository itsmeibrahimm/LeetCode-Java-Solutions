"""add ttl to auth_request table

Revision ID: 16e7899664d5
Revises: 1c476cfd86c3
Create Date: 2020-01-09 10:59:57.330635

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "16e7899664d5"
down_revision = "1c476cfd86c3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("auth_request", sa.Column("expire_sec", sa.BigInteger()))


def downgrade():
    op.drop_column("auth_request", "expire_sec")
