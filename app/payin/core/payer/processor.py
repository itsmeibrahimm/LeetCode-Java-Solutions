import logging
from typing import Optional

from asyncpg import DataError

from app.commons.utils.uuid import generate_object_uuid, ResourceUuidPrefix
from app.payin.core.exceptions import (
    PayerReadError,
    PayerCreationError,
    PayinErrorCode,
    payin_error_message_maps,
    PayerUpdateError,
)
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

    # step 1: lookup active payer by dd_payer_id + payer_type, return error if payer already exists

    # step 2: create PGP customer
    provider = "stripe"
    stripe_customer_id = "{}_{}_{}".format("cus", dd_payer_id, email)
    stripe_default_card = "test_stripe_default_card"
    stripe_default_source = "test_stripe_default_source"

    # step 3: create payer object
    payer: Payer = await pr.payer_repo.insert_payer(
        payer_id=generate_object_uuid(ResourceUuidPrefix.PAYER),
        payer_type=payer_type.value,
        dd_payer_id=dd_payer_id,
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
        try:
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
        except DataError as e:
            logger.error(
                "[onboard_payer][{}] DataError when writing into db.".format(
                    payer.payer_id, e
                )
            )
            raise PayerCreationError(
                error_code=PayinErrorCode.PAYER_CREATION_INVALID_DATA,
                error_message=payin_error_message_maps[
                    PayinErrorCode.PAYER_CREATION_INVALID_DATA.value
                ],
                retryable=True,
            )
    else:
        logger.info(
            "[onboard_payer][%s] skip stripe_customer object creation. payer_type=%s",
            payer.payer_id,
            payer_type,
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
        dd_payer_id=dd_payer_id,
        description=description,
        created_at=payer.created_at,
        updated_at=payer.updated_at,
    )


async def retrieve_payer(payer_id: str) -> Payer:
    # FIXME: should be move into app_context.
    from app.payin.payin import payin_repositories as pr

    # TODO: should consider exposing a parameter to enforce update from PGP
    try:
        payer: Optional[Payer] = await pr.payer_repo.get_payer_by_id(
            payer_id
        ) if payer_id.startswith(
            ResourceUuidPrefix.PAYER.value
        ) else await pr.payer_repo.get_payer_by_stripe_customer_id(
            payer_id
        )
    except DataError as e:
        logger.error(
            "[retrieve_payer][{}] DataError when read from db.".format(payer_id), e
        )
        raise PayerCreationError(
            error_code=PayinErrorCode.PAYER_READ_INVALID_DATA,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYER_READ_INVALID_DATA.value
            ],
            retryable=True,
        )
    if not payer:
        logger.info("[retrieve_payer][%s] not found", payer_id)
        raise PayerReadError(
            error_code=PayinErrorCode.PAYER_READ_NOT_FOUND.value,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYER_READ_NOT_FOUND.value
            ],
            retryable=False,
        )

    return payer


async def update_payer_default_payment_method(
    payer_id: str, default_payment_method_id: str
) -> Payer:
    # FIXME: should be move into app_context.
    from app.payin.payin import payin_repositories as pr

    # Step 1: identify payer's target PGP from payment_methods table by payment_method_id
    if payer_id.startswith(ResourceUuidPrefix.PAYER.value):
        # step 1: identify payer's target PGP from payment_methods table by payment_method_id
        pgp_code = "stripe"
        try:
            pgp_customer: Optional[
                PgpCustomer
            ] = await pr.pgp_customer_repo.get_pgp_customer_by_payer_id_and_pgp_code(
                payer_id=payer_id, pgp_code=pgp_code
            )
        except DataError as e:
            logger.error(
                "[update_payer_data][{}] DataError when read db.".format(payer_id), e
            )
            raise PayerUpdateError(
                error_code=PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value,
                error_message=payin_error_message_maps[
                    PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value
                ],
                retryable=True,
            )
        if not pgp_customer:
            logger.info("[update_payer_data][%s] not found", payer_id)
            raise PayerUpdateError(
                error_code=PayinErrorCode.PAYER_UPDATE_NOT_FOUND.value,
                error_message=payin_error_message_maps[
                    PayinErrorCode.PAYER_UPDATE_NOT_FOUND.value
                ],
                retryable=False,
            )
        logger.info(
            "[update_payer_data][%s] pgp_resource_id=%s",
            payer_id,
            pgp_customer.pgp_resource_id,
        )

        # step 2: call PGP/stripe api to update customer's default source

        # step 3: update default_source in paymentdb_pgp_customer table
        try:
            updated_pgp_cus: PgpCustomer = await pr.pgp_customer_repo.update_pgp_customer_default_payment_method(
                pgp_customer_id=pgp_customer.id,
                default_payment_method_id=default_payment_method_id,
            )
            logger.info("updated_pgp_cus", updated_pgp_cus)
        except DataError as e:
            logger.error(
                "[update_payer_data][{}] DataError when update db.".format(payer_id), e
            )
            raise PayerUpdateError(
                error_code=PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value,
                error_message=payin_error_message_maps[
                    PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value
                ],
                retryable=True,
            )
        return await retrieve_payer(payer_id=payer_id)

    elif payer_id.startswith(ResourceUuidPrefix.STRIPE_CUSTOMER.value):
        logger.info("[update_payer_data][%s] update by stripe customer id", payer_id)
        # step 1: call PGP/stripe api to update customer's default source

        # step 2: update stripe_customer
        try:
            updated_dd_stripe_cus = await pr.stripe_customer_repo.update_stripe_customer_by_stripe_id(
                stripe_customer_id=payer_id, default_source=default_payment_method_id
            )
            logger.info(
                "[update_payer_data][%s] update_stripe_customer_by_stripe_id() completed",
                payer_id,
            )
        except DataError as e:
            logger.error(
                "[update_payer_data][{}] DataError when update  db.".format(payer_id), e
            )
            raise PayerUpdateError(
                error_code=PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value,
                error_message=payin_error_message_maps[
                    PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value
                ],
                retryable=True,
            )

        # step 3: lazy create payer if not available
        return await lazy_create_payer(
            stripe_customer_id=payer_id,
            country=updated_dd_stripe_cus.country_shortname,
            default_payment_method=default_payment_method_id,
        )

    else:
        # step 1: lookup stripe_customer_id by id from maindb_stripe_customer
        dd_stripe_customer: Optional[
            StripeCustomer
        ] = await pr.stripe_customer_repo.get_stripe_customer_by_id(
            primary_id=int(payer_id)
        )
        if not dd_stripe_customer:
            logger.info("[update_payer_data][%s] not found", payer_id)
            raise PayerReadError(
                error_code=PayinErrorCode.PAYER_UPDATE_NOT_FOUND.value,
                error_message=payin_error_message_maps[
                    PayinErrorCode.PAYER_UPDATE_NOT_FOUND.value
                ],
                retryable=False,
            )

        # step 2: call PGP/stripe api to update customer's default source

        # step 3: update default_source in maindb_stripe_customer table
        try:
            updated_dd_stripe_cus = await pr.stripe_customer_repo.update_stripe_customer(
                primary_id=int(payer_id), default_source=default_payment_method_id
            )
            logger.info("updated_dd_stripe_cus", updated_dd_stripe_cus)
        except DataError as e:
            logger.error(
                "[update_payer_data][{}] DataError when update  db.".format(payer_id), e
            )
            raise PayerUpdateError(
                error_code=PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value,
                error_message=payin_error_message_maps[
                    PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value
                ],
                retryable=True,
            )

        # step 4: lazy create payer if not available
        return await lazy_create_payer(
            stripe_customer_id=dd_stripe_customer.stripe_id,
            country=updated_dd_stripe_cus.country_shortname,
            default_payment_method=default_payment_method_id,
            dd_payer_id=str(updated_dd_stripe_cus.owner_id),
        )


async def lazy_create_payer(
    stripe_customer_id: str,
    country: str,
    default_payment_method: str,
    dd_payer_id: Optional[str] = None,
    currency: Optional[str] = None,
    description: Optional[str] = None,
) -> Payer:
    # FIXME: should be move into app_context.
    from app.payin.payin import payin_repositories as pr

    # ensure payer doesn't exist
    exist_payer: Optional[Payer] = await pr.payer_repo.get_payer_by_stripe_customer_id(
        stripe_customer_id=stripe_customer_id
    )
    if exist_payer:
        logger.info(
            "[lazy_create_payer] payer %s already exists, exit!", lazy_create_payer
        )
        return exist_payer

    #
    stripe_customer: Optional[
        StripeCustomer
    ] = await pr.stripe_customer_repo.get_stripe_customer_by_stripe_customer_id(
        stripe_customer_id=stripe_customer_id
    )
    payer_type: str = PayerType.MARKETPLACE.value if not stripe_customer else stripe_customer.owner_type

    # create payer
    payer: Payer = await pr.payer_repo.insert_payer(
        payer_id=generate_object_uuid(ResourceUuidPrefix.PAYER),
        payer_type=payer_type,
        dd_payer_id=dd_payer_id,
        legacy_stripe_customer_id=stripe_customer_id,
        country=country,
        account_balance=0,
        description=description,
    )

    # create pgp_customer for marketplace payer
    if not stripe_customer:
        pgp_code = "stripe"
        await pr.pgp_customer_repo.insert_pgp_customer(
            id=generate_object_uuid(ResourceUuidPrefix.PGP_CUSTOMER),
            pgp_code=pgp_code,
            pgp_resource_id=stripe_customer_id,
            payer_id=payer.payer_id,
            account_balance=0,
            currency=currency,
            default_payment_method=default_payment_method,
            legacy_default_card=None,
            legacy_default_source=default_payment_method,
        )

    return payer
