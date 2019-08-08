from typing import Optional, Any

from asyncpg import DataError

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import ReqContext

# from app.commons.providers import stripe_models as sm
from app.commons.providers.stripe_models import CreateCustomer, CustomerId
from app.commons.types import CountryCode
from app.commons.utils.types import PaymentProvider
from app.commons.utils.uuid import generate_object_uuid, ResourceUuidPrefix
from app.payin.core.exceptions import (
    PayerReadError,
    PayerCreationError,
    PayinErrorCode,
    payin_error_message_maps,
    PayerUpdateError,
)
from app.payin.core.payer.model import Payer, PaymentGatewayProviderCustomer
from app.payin.core.payer.types import PayerType
from app.payin.core.types import PayerIdType
from app.payin.repository.payer_repo import (
    InsertPayerInput,
    InsertPayerOutput,
    InsertPgpCustomerOutput,
    InsertPgpCustomerInput,
    InsertStripeCustomerInput,
    GetPayerByIdInput,
    GetPgpCustomerInput,
    GetPayerByIdOutput,
    GetPgpCustomerOutput,
    UpdatePgpCustomerSetInput,
    UpdatePgpCustomerOutput,
    GetStripeCustomerInput,
    GetStripeCustomerOutput,
    UpdateStripeCustomerSetInput,
    UpdateStripeCustomerOutput,
    UpdateStripeCustomerWhereInput,
    UpdatePgpCustomerWhereInput,
    InsertStripeCustomerOutput,
    PayerRepository,
)


async def create_payer_impl(
    payer_repository: PayerRepository,
    app_ctxt: AppContext,
    req_ctxt: ReqContext,
    dd_payer_id: str,
    payer_type: PayerType,
    email: str,
    country: str,
    description: str,
) -> Payer:
    """
    onboard a new DoorDash payer. We will create 3 models under the hood:
        - Payer
        - PgpCustomer
        - StripeCustomer (for backward compatibility)

    :param payer_repository:
    :param app_ctxt: Application context
    :param req_ctxt: Request context
    :param dd_payer_id: DoorDash client identifier (consumer_id, etc.)
    :param payer_type: Identify the owner type
    :param email: payer email
    :param country: payer country code
    :param description: short description for the payer
    :return: Payer object
    """
    req_ctxt.log.info(
        "[create_payer_impl] dd_payer_id:%s, payer_type:%s",
        dd_payer_id,
        payer_type.value,
    )
    # TODO: we should get pgp_code in different way
    pgp_code = PaymentProvider.STRIPE.value
    # TODO: step 1: lookup active payer by dd_payer_id + payer_type, return error if payer already exists

    # TODO: step 2: create PGP customer
    creat_cus_req: CreateCustomer = CreateCustomer(email=email, description=description)
    try:
        stripe_cus_id: CustomerId = await app_ctxt.stripe.create_customer(
            country=CountryCode(country), request=creat_cus_req
        )
    except Exception as e:
        req_ctxt.log.error(
            "[create_payer_impl][{}] error while creating stripe customer".format(
                dd_payer_id, e
            )
        )
        raise PayerCreationError(
            error_code=PayinErrorCode.PAYER_CREATE_STRIPE_ERROR,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYER_CREATE_STRIPE_ERROR.value
            ],
            retryable=False,
        )
    req_ctxt.log.info(
        "[create_payer_impl][%s] create stripe customer completed. id:%s",
        dd_payer_id,
        stripe_cus_id,
    )

    try:
        # step 3: create payer object
        payer_entity: InsertPayerOutput = await payer_repository.insert_payer(
            request=InsertPayerInput(
                id=generate_object_uuid(ResourceUuidPrefix.PAYER),
                payer_type=payer_type.value,
                dd_payer_id=dd_payer_id,
                legacy_stripe_customer_id=stripe_cus_id,
                country=country,
                description=description,
            )
        )
        req_ctxt.log.info(
            "[create_payer_impl] create payer completed. payer_id:%s", payer_entity.id
        )

        # step 4: create pgp_customer object. We only insert pgp_customer for PayerType.MARKETPLACE
        if payer_type == PayerType.MARKETPLACE.value:
            pgp_customer_entity: InsertPgpCustomerOutput = await payer_repository.insert_pgp_customer(
                request=InsertPgpCustomerInput(
                    id=generate_object_uuid(ResourceUuidPrefix.PGP_CUSTOMER),
                    payer_id=payer_entity.id,
                    pgp_code=pgp_code,
                    pgp_resource_id=stripe_cus_id,
                )
            )
            req_ctxt.log.info(
                "[create_payer_impl][%s] create pgp_customer completed. ppg_customer_id_id:%s",
                payer_entity.id,
                pgp_customer_entity.id,
            )
        else:
            stripe_customer_entity: InsertStripeCustomerOutput = await payer_repository.insert_stripe_customer(
                request=InsertStripeCustomerInput(
                    stripe_id=stripe_cus_id,
                    country_shortname=country,
                    owner_type=payer_type.value,
                    owner_id=int(dd_payer_id),
                )
            )
            req_ctxt.log.info(
                "[create_payer_impl][%s] create stripe_customer completed. stripe_customer_id_id:%s",
                payer_entity.id,
                stripe_customer_entity.id,
            )
    except DataError as e:
        req_ctxt.log.error(
            "[create_payer_impl][{}] DataError when writing into db.".format(
                payer_entity.id, e
            )
        )
        raise PayerCreationError(
            error_code=PayinErrorCode.PAYER_CREATE_INVALID_DATA,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYER_CREATE_INVALID_DATA.value
            ],
            retryable=True,
        )

    return _build_payer(
        payer_entity=payer_entity, pgp_customer_entity=pgp_customer_entity
    )


async def get_payer_impl(
    payer_repository: PayerRepository,
    app_ctxt: AppContext,
    req_ctxt: ReqContext,
    payer_id: str,
    payer_type: Optional[str],
    force_update: Optional[bool] = False,
) -> Payer:
    """
    Retrieve DoorDash payer

    :param app_ctxt: Application context
    :param req_ctxt: Request context
    :param payer_id: payer unique id.
    :param payer_type: Identify the owner type. This is for backward compatibility.
                       Caller can ignore it for new consumer who is onboard from
                       new payer APIs.
    :return: Payer object
    """
    req_ctxt.log.info(
        "[get_payer_impl] payer_id:%s, payer_type:%s", payer_id, payer_type
    )

    # TODO: if force_update is true, we should retrieve the payment_method from GPG

    try:
        if not payer_type or payer_type == PayerType.MARKETPLACE.value:
            mp_payer_entity: Optional[
                GetPayerByIdOutput
            ] = await payer_repository.get_payer_by_id(
                request=GetPayerByIdInput(id=payer_id)
            )
            if not mp_payer_entity:
                err_code = PayinErrorCode.PAYER_READ_NOT_FOUND.value
                raise PayerReadError(
                    error_code=err_code,
                    error_message=payin_error_message_maps[err_code],
                    retryable=False,
                )
            pgp_customer_entity: Optional[
                GetPgpCustomerOutput
            ] = await payer_repository.get_pgp_customer(
                request=GetPgpCustomerInput(payer_id=payer_id, pgp_code="stripe")
            )
            payer = _build_payer(mp_payer_entity, pgp_customer_entity)
        else:
            payer_entity: Optional[
                GetPayerByIdOutput
            ] = await payer_repository.get_payer_by_id(
                request=GetPayerByIdInput(legacy_stripe_customer_id=payer_id)
            )
            if not payer_entity:
                err_code = PayinErrorCode.PAYER_READ_NOT_FOUND.value
                raise PayerReadError(
                    error_code=err_code,
                    error_message=payin_error_message_maps[err_code],
                    retryable=False,
                )
            payer = _build_payer(payer_entity=payer_entity)
    except DataError as e:
        req_ctxt.log.error(
            "[get_payer_impl][{}] DataError when read from db.".format(payer_id), e
        )
        raise PayerCreationError(
            error_code=PayinErrorCode.PAYER_READ_INVALID_DATA,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYER_READ_INVALID_DATA.value
            ],
            retryable=True,
        )

    return payer


async def update_payer_impl(
    payer_repository: PayerRepository,
    app_ctxt: AppContext,
    req_ctxt: ReqContext,
    payer_id: str,
    default_payment_method_id: Optional[str],
    default_source_id: Optional[str],
    default_card_id: Optional[str],
    payer_id_type: Optional[str],
    payer_type: Optional[str],
) -> Payer:
    """
    Update DoorDash payer's default payment method.

    :param payer_repository:
    :param app_ctxt: Application context
    :param req_ctxt: Request context
    :param payer_id: payer unique id.
    :param default_payment_method_id: new default payment_method identity.
    :param default_source_id:
    :param default_card_id:
    :param payer_id_type: Identify the owner type. This is for backward compatibility.
                          Caller can ignore it for new consumer who is onboard from
                          new payer APIs.
    :param payer_type:
    :return: Payer object
    """

    # Step 1: identify payer's target PGP from payment_methods table by payment_method_id
    # if payer_id.startswith(ResourceUuidPrefix.PAYER.value):
    if not payer_id_type:
        # TODO: lookup pgp_payment_methods table to ensure the card is persisted, and get pgp_code.
        pgp_code = "stripe"

        try:
            # ensure customer is present
            pgp_customer_entity: Optional[
                GetPgpCustomerOutput
            ] = await payer_repository.get_pgp_customer(
                GetPgpCustomerInput(payer_id=payer_id, pgp_code=pgp_code)
            )
            if not pgp_customer_entity:
                req_ctxt.log.info("[update_payer_data][%s] not found", payer_id)
                raise PayerUpdateError(
                    error_code=PayinErrorCode.PAYER_UPDATE_NOT_FOUND.value,
                    error_message=payin_error_message_maps[
                        PayinErrorCode.PAYER_UPDATE_NOT_FOUND.value
                    ],
                    retryable=False,
                )
            req_ctxt.log.info(
                "[update_payer_impl][%s] pgp_customer resource id=%s",
                payer_id,
                pgp_customer_entity.pgp_resource_id,
            )

            # TODO: call PGP/stripe api to update default payment method

            # update pgp_customer with new default_payment_method
            updated_pgp_customer_entity: UpdatePgpCustomerOutput = await payer_repository.update_pgp_customer(
                UpdatePgpCustomerSetInput(
                    default_payment_method_id=default_payment_method_id,
                    legacy_default_source_id=default_source_id,
                    legacy_default_card_id=default_card_id,
                ),
                UpdatePgpCustomerWhereInput(id=pgp_customer_entity.id),
            )

            # build response Payer object
            payer_entity: Optional[
                GetPayerByIdOutput
            ] = await payer_repository.get_payer_by_id(
                request=GetPayerByIdInput(id=payer_id)
            )
            return _build_payer(payer_entity, updated_pgp_customer_entity)
        except DataError as e:
            req_ctxt.log.error(
                "[update_payer_impl][{}] DataError when read db.".format(payer_id), e
            )
            raise PayerUpdateError(
                error_code=PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value,
                error_message=payin_error_message_maps[
                    PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value
                ],
                retryable=True,
            )
    elif payer_id_type in (
        PayerIdType.STRIPE_CUSTOMER_ID.value,
        PayerIdType.STRIPE_CUSTOMER_SERIAL_ID.value,
    ):
        req_ctxt.log.info(
            "[update_payer_impl][%s] update by stripe customer id", payer_id
        )

        # lookup stripe_customer to ensure data is present
        stripe_customer_entity: GetStripeCustomerOutput = await payer_repository.get_stripe_customer(
            GetStripeCustomerInput(stripe_id=payer_id)
            if payer_id_type == "stripe_customer_id"
            else GetStripeCustomerInput(id=payer_id)
        )
        if not stripe_customer_entity:
            req_ctxt.log.info("[update_payer_impl][%s] not found", payer_id)
            raise PayerUpdateError(
                error_code=PayinErrorCode.PAYER_UPDATE_NOT_FOUND.value,
                error_message=payin_error_message_maps[
                    PayinErrorCode.PAYER_UPDATE_NOT_FOUND.value
                ],
                retryable=False,
            )

        # TODO: call PGP/stripe api to update default payment method

        # update stripe_customer with new default_payment_method
        # FIXME: need to handle the migration case where payer only updates default_payment_method which
        # is not supported by stripe_customer schema
        updated_stripe_customer_entity: UpdateStripeCustomerOutput = await payer_repository.update_stripe_customer(
            UpdateStripeCustomerSetInput(
                default_source=default_source_id, default_card=default_card_id
            ),
            UpdateStripeCustomerWhereInput(id=stripe_customer_entity.id),
        )

        # lazy create payer if doesn't exist
        return await _lazy_create_payer(
            payer_repository=payer_repository,
            req_ctxt=req_ctxt,
            stripe_customer_id=updated_stripe_customer_entity.stripe_id,
            country=updated_stripe_customer_entity.country_shortname,
            payer_type=payer_type,
            default_payment_method_id=default_payment_method_id,
            default_source_id=default_source_id,
            default_card_id=default_card_id,
        )
    else:
        req_ctxt.log.error(
            "[update_payer_impl][%s] invalid payer_type: %s", payer_id, payer_id_type
        )
        raise PayerUpdateError(
            error_code=PayinErrorCode.PAYER_UPDATE_INVALID_PAYER_TYPE.value,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYER_UPDATE_INVALID_PAYER_TYPE.value
            ],
            retryable=False,
        )


async def _lazy_create_payer(
    payer_repository: PayerRepository,
    req_ctxt: ReqContext,
    stripe_customer_id: str,
    country: str,
    payer_type: Optional[str],
    default_payment_method_id: Optional[str],
    default_source_id: Optional[str],
    default_card_id: Optional[str],
    dd_payer_id: Optional[str] = None,
    currency: Optional[str] = None,
    description: Optional[str] = None,
) -> Payer:
    """
    Perform lazy creation of Payer and PgpCustomer objects.

    :param req_ctxt: Request context
    :param stripe_customer_id:
    :param country:
    :param payer_type:
    :param default_payment_method_id:
    :param default_source_id:
    :param default_card_id:
    :param dd_payer_id:
    :param currency:
    :param description:
    :return: Payer object
    """

    # ensure Payer doesn't exist
    get_payer_entity: Optional[
        GetPayerByIdOutput
    ] = await payer_repository.get_payer_by_id(
        request=GetPayerByIdInput(legacy_stripe_customer_id=stripe_customer_id)
    )
    if get_payer_entity:
        req_ctxt.log.info(
            "[_lazy_create_payer] payer already exist for stipe_customer %s . payer_id:%s",
            stripe_customer_id,
            get_payer_entity.id,
        )
        return _build_payer(payer_entity=get_payer_entity)

    # create Payer object
    payer_entity: InsertPayerOutput = await payer_repository.insert_payer(
        request=InsertPayerInput(
            id=generate_object_uuid(ResourceUuidPrefix.PAYER),
            payer_type=payer_type,
            dd_payer_id=dd_payer_id,
            legacy_stripe_customer_id=stripe_customer_id,
            country=country,
            description=description,
        )
    )

    # create pgp_customer for marketplace
    if payer_type == PayerType.MARKETPLACE.value:
        pgp_code = "stripe"
        pgp_customer_entity: InsertPgpCustomerOutput = await payer_repository.insert_pgp_customer(
            request=InsertPgpCustomerInput(
                id=generate_object_uuid(ResourceUuidPrefix.PGP_CUSTOMER),
                payer_id=payer_entity.id,
                pgp_code=pgp_code,
                pgp_resource_id=stripe_customer_id,
                currency=currency,
                default_payment_method_id=default_payment_method_id,
                default_source_id=default_source_id,
                default_card_id=default_card_id,
            )
        )
        return _build_payer(
            payer_entity=payer_entity, pgp_customer_entity=pgp_customer_entity
        )

    return _build_payer(payer_entity=payer_entity)


def _build_payer(
    payer_entity: Any,  # GetPayerByIdOutput,
    pgp_customer_entity: Optional[Any] = None,  # GetPgpCustomerOutput
) -> Payer:
    """
    Build Payer object.

    :param payer_entity:
    :param pgp_customer_entity:
    :return: Payer object
    """
    provider_customer: PaymentGatewayProviderCustomer = PaymentGatewayProviderCustomer(
        payment_provider=pgp_customer_entity.pgp_code,
        payment_provider_customer_id=pgp_customer_entity.pgp_resource_id,
    ) if pgp_customer_entity else PaymentGatewayProviderCustomer(
        payment_provider="stripe",
        payment_provider_customer_id=payer_entity.legacy_stripe_customer_id,
    )

    return Payer(
        payer_id=payer_entity.id,
        payer_type=payer_entity.payer_type,
        payment_gateway_provider_customers=[provider_customer],
        country=payer_entity.country,
        dd_payer_id=payer_entity.dd_payer_id,
        description=payer_entity.description,
        created_at=payer_entity.created_at,
        updated_at=payer_entity.updated_at,
    )
