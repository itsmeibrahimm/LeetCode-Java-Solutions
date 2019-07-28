import logging

from app.commons.utils.uuid import generate_object_uuid, ResourceUuidPrefix
from app.payin.core.payer.model import (
    Payer,
    PaymentGatewayProviderCustomer,
    PgpCustomer,
    StripeCustomer,
)
from app.payin.core.payer.types import PayerType

logger = logging.getLogger(__name__)


async def onboard_payer(
    dd_payer_id: str, payer_type: PayerType, email: str, country: str, description: str
) -> Payer:
    # FIXME: should be move into app_context.
    from app.payin.payin import payin_repositories as pr

    # Step 1: lookup active payer by dd_payer_id + payer_type, return error if payer already exists

    # Step 2: create PGP customer
    provider = "stripe"
    stripe_customer_id = "{}_{}".format("test_stripe_customer_id", email)
    stripe_default_card = "test_stripe_default_card"
    stripe_default_source = "test_stripe_default_source"

    # step 3: create payer object
    payer: Payer = await pr.payer_repo.insert_payer(
        payer_id=generate_object_uuid(ResourceUuidPrefix.PAYER),
        payer_type=payer_type.value,
        dd_payer_id=int(dd_payer_id),
        legacy_stripe_customer_id=stripe_customer_id,
        country=country,
        account_balance=0,
        description=description,
    )

    # step 4: create pgp_customer object. We only insert pgp_customer for PayerType.MARKETPLACE
    pgp_customer_uuid = generate_object_uuid(ResourceUuidPrefix.PGP_CUSTOMER)
    pgp_code = "stripe"
    pgp_resource_id = "cus_stripe_customer_id"
    currency = "US"
    pgp_customer: PgpCustomer = await pr.pgp_customer_repo.insert_pgp_customer(
        id=pgp_customer_uuid,
        pgp_code=pgp_code,
        pgp_resource_id=pgp_resource_id,
        payer_id=payer.payer_id,
        account_balance=0,
        currency=currency,
        default_payment_method=None,
        legacy_default_card=stripe_default_card,
        legacy_default_source=stripe_default_source,
    )
    logger.info(
        "onboard_payer() insert_pgp_customer comppleted. id=%s", pgp_customer.id
    )

    # step 5: create stripe_customer object except "marketplace" payer
    if payer_type != PayerType.MARKETPLACE.value:
        stripe_customer: StripeCustomer = await pr.stripe_customer_repo.insert_stripe_customer(
            stripe_customer_id=stripe_customer_id,
            country=country,
            owner_type=payer_type.value,
            owner_id=int(dd_payer_id),
            default_card=stripe_default_card,
            default_source=stripe_default_source,
        )
        logger.info(
            "insert_stripe_customer() completed. stripe_customer_id=%s",
            stripe_customer.id,
        )

    # construct response Payer object
    provider_customer: PaymentGatewayProviderCustomer = PaymentGatewayProviderCustomer(
        payment_provider=provider, payment_provider_customer_id=stripe_customer_id
    )
    return Payer(
        payer_id=payer.payer_id,
        payer_type=payer_type,
        payment_gateway_provider_customers=[provider_customer],
        country=country,
        dd_payer_id=int(dd_payer_id),
        description=description,
        created_at=payer.created_at,
        updated_at=payer.updated_at,
    )
