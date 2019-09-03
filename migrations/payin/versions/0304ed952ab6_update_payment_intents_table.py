"""update payment_intents table

Revision ID: 0304ed952ab6
Revises: 1320391a3ba3
Create Date: 2019-08-29 13:49:30.774071

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0304ed952ab6"
down_revision = "1320391a3ba3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "payment_intents",
        sa.Column(
            "payment_method_id",
            sa.String(255),
            sa.schema.ForeignKey("pgp_payment_methods.id"),
            nullable=True,
        ),
    )


def downgrade():
    pass
