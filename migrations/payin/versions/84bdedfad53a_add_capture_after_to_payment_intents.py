"""add capture_after to payment intents

Revision ID: 84bdedfad53a
Revises: f47a4d690309
Create Date: 2019-08-29 12:41:45.266746

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "84bdedfad53a"
down_revision = "f47a4d690309"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payment_intents", sa.Column("capture_after", sa.DateTime))


def downgrade():
    op.drop_column("payment_intents", "capture_after")
