"""add index for payin models

Revision ID: ffe22b33f903
Revises: 5442a422c00a
Create Date: 2019-09-24 12:41:12.369319

"""
from alembic import op


# revision identifiers, used by Alembic.
from sqlalchemy import text

revision = "ffe22b33f903"
down_revision = "5442a422c00a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "pgp_payment_methods_pgp_resource_id_idx",
        "pgp_payment_methods",
        ["pgp_resource_id"],
    )
    op.create_index(
        "payment_intents_status_capture_after_idx",
        "payment_intents",
        ["status", text("capture_after ASC NULLS FIRST")],
    )
    op.create_index(
        "payment_intents_status_updated_at_idx",
        "payment_intents",
        ["status", text("updated_at DESC NULLS LAST")],
    )
    op.create_index(
        "payment_intents_idempotency_key_idx", "payment_intents", ["idempotency_key"]
    )
    op.create_index(
        "payment_intents_cart_payment_id_idx", "payment_intents", ["cart_payment_id"]
    )
    op.create_index(
        "pgp_payment_intents_payment_intent_id_fkey",
        "pgp_payment_intents",
        ["payment_intent_id"],
    )
    op.create_index(
        "pgp_payment_intents_charge_resource_id_fkey",
        "pgp_payment_intents",
        ["charge_resource_id"],
    )
    op.create_index(
        "payment_charges_payment_intent_id_fkey",
        "payment_charges",
        ["payment_intent_id"],
    )
    op.create_index(
        "pgp_payment_charges_payment_charge_id_fkey",
        "pgp_payment_charges",
        ["payment_charge_id"],
    )

    # payers
    op.create_index(
        "payers_dd_payer_id_payer_type_idx", "payers", ["dd_payer_id", "payer_type"]
    )
    op.create_index("pgp_customers_payer_id_fkey", "pgp_customers", ["payer_id"])


def downgrade():
    op.drop_index("pgp_payment_methods_pgp_resource_id_idx")
    op.drop_index("payment_intents_status_capture_after_idx")
    op.drop_index("payment_intents_status_updated_at_idx")
    op.drop_index("payment_intents_idempotency_key_idx")
    op.drop_index("payment_intents_cart_payment_id_idx")
    op.drop_index("pgp_payment_intents_payment_intent_id_fkey")
    op.drop_index("pgp_payment_intents_charge_resource_id_fkey")
    op.drop_index("payment_charges_payment_intent_id_fkey")
    op.drop_index("pgp_payment_charges_payment_charge_id_fkey")
    op.drop_index("payers_dd_payer_id_payer_type_idx")
    op.drop_index("pgp_customers_payer_id_fkey")
