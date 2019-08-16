from datetime import datetime
from typing import Optional, Tuple

from asyncpg import DataError

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import ReqContext

from app.commons.providers.stripe_models import (
    CreateCustomer,
    CustomerId,
    UpdateCustomer,
)
from app.commons.types import CountryCode
from app.commons.utils.types import PaymentProvider
from app.commons.utils.uuid import generate_object_uuid, ResourceUuidPrefix
from app.payin.core.exceptions import (
    PayerReadError,
    PayerCreationError,
    PayinErrorCode,
    PayerUpdateError,
)
from app.payin.core.payer.model import Payer, PaymentGatewayProviderCustomer
from app.payin.core.payer.types import PayerType
from app.payin.core.payment_method.processor import get_payment_method
from app.payin.core.types import PayerIdType
from app.payin.repository.payer_repo import (
    InsertPayerInput,
    InsertPgpCustomerInput,
    InsertStripeCustomerInput,
    GetPayerByIdInput,
    UpdatePgpCustomerSetInput,
    GetStripeCustomerInput,
    UpdateStripeCustomerSetInput,
    UpdateStripeCustomerWhereInput,
    UpdatePgpCustomerWhereInput,
    PayerRepository,
    PayerDbEntity,
    PgpCustomerDbEntity,
    StripeCustomerDbEntity,
    GetPayerByDDPayerIdAndTypeInput,
)
from app.payin.repository.payment_method_repo import PaymentMethodRepository


async def create_payer_impl(
    payer_repository: PayerRepository,
    app_ctxt: AppContext,
    req_ctxt: ReqContext,
    dd_payer_id: str,
    payer_type: str,
    email: str,
    country: str,
    description: str,
) -> Payer:
    """
    create a new DoorDash payer. We will create 3 models under the hood:
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
        f"[create_payer_impl] dd_payer_id:{dd_payer_id}, payer_type:{payer_type}"
    )
    # TODO: we should get pgp_code in different way
    pgp_code = PaymentProvider.STRIPE.value

    # step 1: lookup active payer by dd_payer_id + payer_type, return error if payer already exists
    try:
        exist_payer: Optional[
            PayerDbEntity
        ] = await payer_repository.get_payer_by_dd_payer_id_and_payer_type(
            GetPayerByDDPayerIdAndTypeInput(
                dd_payer_id=dd_payer_id, payer_type=payer_type
            )
        )
        if exist_payer:
            req_ctxt.log.error(
                f"[create_payer_impl][{exist_payer.id}] payer already exists. dd_payer_id:[{dd_payer_id}], payer_type:[{payer_type}]"
            )
            # raise PayerCreationError(
            #     error_code=PayinErrorCode.PAYER_CREATE_PAYER_ALREADY_EXIST,
            #     retryable=False,
            # )
    except DataError as e:
        req_ctxt.log.error(
            f"[create_payer_impl][{dd_payer_id}] DataError when reading from payers table: {e}"
        )
        raise PayerCreationError(
            error_code=PayinErrorCode.PAYER_READ_DB_ERROR, retryable=True
        )

    # step 2: create PGP customer
    creat_cus_req: CreateCustomer = CreateCustomer(email=email, description=description)
    try:
        stripe_cus_id: CustomerId = await app_ctxt.stripe.create_customer(
            country=CountryCode(country), request=creat_cus_req
        )
    except Exception as e:
        req_ctxt.log.error(
            f"[create_payer_impl][{dd_payer_id}] error while creating stripe customer. {e}"
        )
        raise PayerCreationError(
            error_code=PayinErrorCode.PAYER_CREATE_STRIPE_ERROR, retryable=False
        )

    req_ctxt.log.info(
        f"[create_payer_impl][{dd_payer_id}] create PGP customer completed. id:[{stripe_cus_id}]"
    )

    # step 3: create Payer/PgpCustomer/StripeCustomer objects
    payer_entity, pgp_customer_entity, stripe_customer_entity = await _create_payer_raw_objects(
        app_ctxt=app_ctxt,
        req_ctxt=req_ctxt,
        dd_payer_id=dd_payer_id,
        payer_type=payer_type,
        country=country,
        pgp_customer_id=stripe_cus_id,
        pgp_code=pgp_code,
        description=description,
    )

    return _build_payer(
        payer_entity=payer_entity,
        pgp_customer_entity=pgp_customer_entity,
        stripe_customer_entity=stripe_customer_entity,
    )


async def get_payer_impl(
    app_ctxt: AppContext,
    req_ctxt: ReqContext,
    payer_id: str,
    payer_id_type: Optional[str],
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
    :param payer_id_type: [string] identify the type of payer_id. Valid values include "dd_payer_id",
           "stripe_customer_id", "stripe_customer_serial_id" (default is "dd_payer_id")
    :return: Payer object
    """
    req_ctxt.log.info(
        "[get_payer_impl] payer_id:%s, payer_id_type:%s", payer_id, payer_id_type
    )

    # TODO: if force_update is true, we should retrieve the customer from PGP

    payer: Payer = await get_payer_object(
        app_ctxt=app_ctxt,
        req_ctxt=req_ctxt,
        payer_id=payer_id,
        payer_id_type=payer_id_type,
        payer_type=payer_type,
    )
    return payer


async def update_payer_impl(
    payer_repository: PayerRepository,
    app_ctxt: AppContext,
    req_ctxt: ReqContext,
    payer_id: str,
    default_payment_method_id: str,
    country: CountryCode = CountryCode.US,
    payer_id_type: Optional[str] = None,
    payer_type: Optional[str] = None,
    payment_method_id_type: Optional[str] = None,
) -> Payer:
    """
    Update DoorDash payer's default payment method.

    :param payer_repository:
    :param app_ctxt: Application context
    :param req_ctxt: Request context
    :param payer_id: payer unique id.
    :param default_payment_method_id: new default payment_method identity.
    :param payer_id_type: Identify the owner type. This is for backward compatibility.
                          Caller can ignore it for new consumer who is onboard from
                          new payer APIs.
    :param payer_type:
    :param payment_method_id_type:
    :return: Payer object
    """

    # step 1: find Payer object to get pgp_resource_id. Exception is handled by get_payer_object()
    payer_entity, pgp_cus_entity, stripe_cus_entity = await get_payer_raw_objects(
        app_ctxt=app_ctxt,
        req_ctxt=req_ctxt,
        payer_id=payer_id,
        payer_id_type=payer_id_type,
        payer_type=payer_type,
    )

    # step 2: find PaymentMethod object to get pgp_resource_id.
    pm_entity, sc_entity = await get_payment_method(
        payment_method_repository=PaymentMethodRepository(context=app_ctxt),
        req_ctxt=req_ctxt,
        payer_id=payer_id,
        payment_method_id=default_payment_method_id,
        payer_id_type=payer_id_type,
        payment_method_id_type=payment_method_id_type,
    )

    # step 3: call PGP/stripe api to update default payment method
    pgp_cus_id: str
    if pgp_cus_entity:
        pgp_cus_id = pgp_cus_entity.pgp_resource_id
    elif stripe_cus_entity:
        pgp_cus_id = stripe_cus_entity.stripe_id
    update_cus_req: UpdateCustomer = UpdateCustomer(
        sid=pgp_cus_id,
        invoice_settings=UpdateCustomer.InvoiceSettings(
            default_payment_method=sc_entity.stripe_id
        ),
    )
    try:
        input_country = CountryCode(payer_entity.country) if payer_entity else country
        stripe_customer = await app_ctxt.stripe.update_customer(
            country=input_country, request=update_cus_req
        )
    except Exception as e:
        req_ctxt.log.error(
            f"[update_payer_impl][{payer_id}][{payer_id_type}] error while updating stripe customer {e}"
        )
        raise PayerUpdateError(
            error_code=PayinErrorCode.PAYER_UPDATE_STRIPE_ERROR, retryable=False
        )

    req_ctxt.log.info(
        f"[update_payer_impl][{payer_id}][{payer_id_type}] PGP update default_payment_method completed:[{stripe_customer.invoice_settings.default_payment_method}]"
    )

    # step 4: update default_payment_method in pgp_customers/stripe_customer table
    resp_payer: Payer
    try:
        if not payer_id_type or payer_id_type in (
            PayerIdType.DD_PAYMENT_PAYER_ID.value,
            PayerIdType.DD_CONSUMER_ID.value,
        ):
            if pgp_cus_entity:
                where_input: UpdatePgpCustomerWhereInput = UpdatePgpCustomerWhereInput(
                    id=pgp_cus_entity.id
                )
                updated_pgp_customer_entity: PgpCustomerDbEntity = await payer_repository.update_pgp_customer(
                    UpdatePgpCustomerSetInput(
                        default_payment_method_id=sc_entity.stripe_id
                    ),
                    where_input,
                )
            req_ctxt.log.info(
                f"[update_payer_impl][{payer_id}][{payer_id_type}] pgp_customers update default_payment_method completed:[{default_payment_method_id}]"
            )

            resp_payer = _build_payer(
                payer_entity=payer_entity,
                pgp_customer_entity=updated_pgp_customer_entity,
            )
        elif payer_id_type in (
            PayerIdType.STRIPE_CUSTOMER_SERIAL_ID.value,
            PayerIdType.STRIPE_CUSTOMER_ID.value,
        ):
            # update stripe_customer with new default_payment_method
            if stripe_cus_entity:
                updated_stripe_cus_entity = await payer_repository.update_stripe_customer(
                    UpdateStripeCustomerSetInput(
                        default_card=default_payment_method_id
                    ),
                    UpdateStripeCustomerWhereInput(id=stripe_cus_entity.id),
                )
                req_ctxt.log.info(
                    f"[update_payer_impl][{payer_id}][{payer_id_type}] stripe_customer update default_payment_method completed:[{default_payment_method_id}]"
                )

                # lazy create payer if doesn't exist
                resp_payer = await _lazy_create_payer(
                    app_ctxt=app_ctxt,
                    req_ctxt=req_ctxt,
                    pgp_customer_id=updated_stripe_cus_entity.stripe_id,
                    country=updated_stripe_cus_entity.country_shortname,
                    pgp_code=PaymentProvider.STRIPE.value,
                    description=stripe_customer.description,
                    dd_payer_id=str(updated_stripe_cus_entity.owner_id),
                    payer_type=updated_stripe_cus_entity.owner_type,
                    default_payment_method_id=default_payment_method_id,
                )
        else:
            req_ctxt.log.error(
                f"[update_payer_impl][{payer_id}][{payer_id_type}] invalid payer_id_type"
            )
            raise PayerReadError(
                error_code=PayinErrorCode.PAYER_READ_INVALID_DATA, retryable=False
            )
    except DataError as e:
        req_ctxt.log.error(
            f"[get_payer_entity] DataError when reading data from db: {e}"
        )
        raise PayerReadError(
            error_code=PayinErrorCode.PAYER_READ_DB_ERROR, retryable=False
        )

    return resp_payer


async def get_payer_object(
    app_ctxt: AppContext,
    req_ctxt: ReqContext,
    payer_id: str,
    payer_id_type: Optional[str],
    payer_type: Optional[str],
) -> Payer:
    """
    Utility function to get Payer object.
    :param app_ctxt: application context
    :param req_ctxt: request context
    :param payer_id: payer id
    :param payer_id_type: type of payer id. Refer to PayerIdType
    :return: Payer object
    """
    payer_entity, pgp_cus_entity, stripe_cus_entity = await get_payer_raw_objects(
        app_ctxt=app_ctxt,
        req_ctxt=req_ctxt,
        payer_id=payer_id,
        payer_id_type=payer_id_type,
        payer_type=payer_type,
    )

    # build Payer object
    return _build_payer(
        payer_entity=payer_entity,
        pgp_customer_entity=pgp_cus_entity,
        stripe_customer_entity=stripe_cus_entity,
    )


async def get_payer_raw_objects(
    app_ctxt: AppContext,
    req_ctxt: ReqContext,
    payer_id: str,
    payer_id_type: Optional[str],
    payer_type: Optional[str],
) -> Tuple[
    Optional[PayerDbEntity],
    Optional[PgpCustomerDbEntity],
    Optional[StripeCustomerDbEntity],
]:
    """
    Utility function to get Payer raw objects.
    :param app_ctxt: application context
    :param req_ctxt: request context
    :param payer_id: payer id
    :param payer_id_type: type of payer id. Refer to PayerIdType
    :param payer_type: type of payer. Refer to PayerType
    :return: Tuple of PayerDbEntity, PgpCustomerDbEntity, StripeCustomerDbEntity
    """
    payer_entity: Optional[PayerDbEntity] = None
    pgp_cus_entity: Optional[PgpCustomerDbEntity] = None
    stripe_cus_entity: Optional[StripeCustomerDbEntity] = None
    is_found: bool = False
    payer_repo: PayerRepository = PayerRepository(app_ctxt)
    try:
        if not payer_id_type or payer_id_type in (
            PayerIdType.DD_PAYMENT_PAYER_ID.value,
            PayerIdType.DD_CONSUMER_ID.value,
        ):
            payer_entity, pgp_cus_entity = await payer_repo.get_payer_and_pgp_customer_by_id(
                input=GetPayerByIdInput(dd_payer_id=payer_id)
                if payer_id_type == PayerIdType.DD_CONSUMER_ID.value
                else GetPayerByIdInput(id=payer_id)
            )
            is_found = True if (payer_entity and pgp_cus_entity) else False
        elif payer_id_type in (
            PayerIdType.STRIPE_CUSTOMER_SERIAL_ID.value,
            PayerIdType.STRIPE_CUSTOMER_ID.value,
        ):
            if payer_type and payer_type != PayerType.MARKETPLACE:
                stripe_cus_entity = await payer_repo.get_stripe_customer(
                    GetStripeCustomerInput(stripe_id=payer_id)
                    if payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID.value
                    else GetStripeCustomerInput(id=payer_id)
                )
                # payer entity is optional
                payer_entity = await payer_repo.get_payer_by_id(
                    request=GetPayerByIdInput(legacy_stripe_customer_id=payer_id)
                )
                is_found = True if stripe_cus_entity else False
            else:
                req_ctxt.log.info(
                    f"[get_payer_raw_objects][{payer_id}] no record in db, should retrieve from stripe. [{payer_id_type}] [{payer_type}]"
                )
        else:
            req_ctxt.log.error(
                "[get_payer_entity][%s] invalid payer_id_type:[%s]",
                payer_id,
                payer_id_type,
            )
            raise PayerReadError(
                error_code=PayinErrorCode.PAYER_READ_INVALID_DATA, retryable=False
            )
    except DataError as e:
        req_ctxt.log.error(
            f"[get_payer_entity] DataError when reading data from db: {e}"
        )
        raise PayerReadError(
            error_code=PayinErrorCode.PAYER_READ_DB_ERROR, retryable=False
        )

    if not is_found:
        req_ctxt.log.error(
            "[get_payer_entity][%s] payer not found:[%s]", payer_id, payer_id_type
        )
        raise PayerReadError(
            error_code=PayinErrorCode.PAYER_READ_NOT_FOUND, retryable=False
        )

    return payer_entity, pgp_cus_entity, stripe_cus_entity


async def _create_payer_raw_objects(
    app_ctxt: AppContext,
    req_ctxt: ReqContext,
    dd_payer_id: str,
    payer_type: str,
    country: str,
    pgp_customer_id: str,
    pgp_code: str,
    description: Optional[str],
    default_payment_method_id: Optional[str] = None,
) -> Tuple[
    Optional[PayerDbEntity],
    Optional[PgpCustomerDbEntity],
    Optional[StripeCustomerDbEntity],
]:
    payer_repository = PayerRepository(context=app_ctxt)
    try:
        payer_entity: PayerDbEntity
        pgp_customer_entity: Optional[PgpCustomerDbEntity] = None
        stripe_customer_entity: Optional[StripeCustomerDbEntity] = None
        payer_id = generate_object_uuid(ResourceUuidPrefix.PAYER)
        payer_input = InsertPayerInput(
            id=payer_id,
            payer_type=payer_type,
            dd_payer_id=dd_payer_id,
            legacy_stripe_customer_id=pgp_customer_id,
            country=country,
            description=description,
        )
        if payer_type == PayerType.MARKETPLACE.value:
            # create Payer and PgpCustomer objects
            pgp_customer_input = InsertPgpCustomerInput(
                id=generate_object_uuid(ResourceUuidPrefix.PGP_CUSTOMER),
                payer_id=payer_id,
                pgp_code=pgp_code,
                pgp_resource_id=pgp_customer_id,
                default_payment_method_id=default_payment_method_id,
            )
            payer_entity, pgp_customer_entity = await payer_repository.insert_payer_and_pgp_customer(
                payer_input=payer_input, pgp_customer_input=pgp_customer_input
            )
            req_ctxt.log.info(
                "[create_payer_impl][%s] create payer/pgp_customer completed. stripe_customer_id_id:%s",
                payer_entity.id,
                pgp_customer_id,
            )
        else:
            # create Payer and StripeCustomer objects
            payer_entity = await payer_repository.insert_payer(request=payer_input)
            req_ctxt.log.info(
                "[create_payer_impl][%s] create payer completed. stripe_customer_id_id:%s",
                payer_entity.id,
                pgp_customer_id,
            )
            stripe_customer_entity = await payer_repository.get_stripe_customer(
                GetStripeCustomerInput(stripe_id=pgp_customer_id)
            )
            if not stripe_customer_entity:
                stripe_customer_entity = await payer_repository.insert_stripe_customer(
                    request=InsertStripeCustomerInput(
                        stripe_id=pgp_customer_id,
                        country_shortname=country,
                        owner_type=payer_type,
                        owner_id=int(dd_payer_id),
                        default_card=default_payment_method_id,
                    )
                )
            req_ctxt.log.info(
                "[create_payer_impl][%s] create stripe_customer completed. stripe_customer.id:%s",
                payer_entity.id,
                stripe_customer_entity.id,
            )
    except DataError as e:
        req_ctxt.log.error(
            f"[create_payer_impl][{payer_entity.id}] DataError when writing into db. {e}"
        )
        raise PayerCreationError(
            error_code=PayinErrorCode.PAYER_CREATE_INVALID_DATA, retryable=True
        )

    return payer_entity, pgp_customer_entity, stripe_customer_entity


async def _lazy_create_payer(
    app_ctxt: AppContext,
    req_ctxt: ReqContext,
    dd_payer_id: str,
    country: str,
    pgp_customer_id: str,
    pgp_code: str,
    payer_type: str,
    default_payment_method_id: Optional[str],
    description: Optional[str] = None,
) -> Payer:
    """
    Internal function for lazy creation of payer.

    :param app_ctxt:
    :param req_ctxt:
    :param dd_payer_id:
    :param payer_type:
    :param country:
    :param pgp_customer_id:
    :param pgp_code:
    :param default_payment_method_id:
    :param description:
    :return: Payer object
    """

    # ensure Payer doesn't exist
    payer_repository = PayerRepository(context=app_ctxt)
    get_payer_entity: Optional[PayerDbEntity] = await payer_repository.get_payer_by_id(
        request=GetPayerByIdInput(legacy_stripe_customer_id=pgp_customer_id)
    )
    if get_payer_entity:
        req_ctxt.log.info(
            "[_lazy_create_payer] payer already exist for stipe_customer %s . payer_id:%s",
            pgp_customer_id,
            get_payer_entity.id,
        )
        return _build_payer(payer_entity=get_payer_entity)

    payer_entity, pgp_customer_entity, stripe_customer_entity = await _create_payer_raw_objects(
        app_ctxt=app_ctxt,
        req_ctxt=req_ctxt,
        dd_payer_id=dd_payer_id,
        payer_type=payer_type,
        country=country,
        pgp_customer_id=pgp_customer_id,
        pgp_code=pgp_code,
        description=description,
        default_payment_method_id=default_payment_method_id,
    )
    return _build_payer(
        payer_entity=payer_entity,
        pgp_customer_entity=pgp_customer_entity,
        stripe_customer_entity=stripe_customer_entity,
    )


def _build_payer(
    payer_entity: Optional[PayerDbEntity] = None,
    pgp_customer_entity: Optional[PgpCustomerDbEntity] = None,
    stripe_customer_entity: Optional[StripeCustomerDbEntity] = None,
) -> Payer:
    """
    Build Payer object.

    :param payer_entity:
    :param pgp_customer_entity:
    :param stripe_customer_entity:
    :return: Payer object
    """
    payer: Payer
    provider_customer: PaymentGatewayProviderCustomer

    if payer_entity:
        if pgp_customer_entity:
            provider_customer = PaymentGatewayProviderCustomer(
                payment_provider=pgp_customer_entity.pgp_code,
                payment_provider_customer_id=pgp_customer_entity.pgp_resource_id,
                default_payment_method_id=pgp_customer_entity.default_payment_method_id,
            )
        else:
            provider_customer = PaymentGatewayProviderCustomer(
                payment_provider=PaymentProvider.STRIPE.value,  # hard-coded "stripe"
                payment_provider_customer_id=payer_entity.legacy_stripe_customer_id,
            )
        payer = Payer(
            id=payer_entity.id,
            payer_type=payer_entity.payer_type,
            payment_gateway_provider_customers=[provider_customer],
            country=payer_entity.country,
            dd_payer_id=payer_entity.dd_payer_id,
            description=payer_entity.description,
            created_at=payer_entity.created_at,
            updated_at=payer_entity.updated_at,
        )
    elif stripe_customer_entity:
        provider_customer = PaymentGatewayProviderCustomer(
            payment_provider=PaymentProvider.STRIPE.value,  # hard-coded "stripe"
            payment_provider_customer_id=stripe_customer_entity.stripe_id,
            default_payment_method_id=stripe_customer_entity.default_card,
        )
        if payer_entity:
            payer = Payer(
                id=payer_entity.id,
                payer_type=payer_entity.payer_type,
                payment_gateway_provider_customers=[provider_customer],
                country=payer_entity.country,
                dd_payer_id=payer_entity.dd_payer_id,
                description=payer_entity.description,
                created_at=payer_entity.created_at,
                updated_at=payer_entity.updated_at,
            )
        else:
            payer = Payer(
                id=stripe_customer_entity.stripe_id,  # FIXME: ensure payer lazy creation
                created_at=datetime.utcnow(),  # FIXME: ensure payer lazy creation
                updated_at=datetime.utcnow(),  # FIXME: ensure payer lazy creation
                country=stripe_customer_entity.country_shortname,
                dd_payer_id=str(stripe_customer_entity.owner_id),
                # payer_type=stripe_customer_entity.owner_type,
                payment_gateway_provider_customers=[provider_customer],
            )

    return payer
