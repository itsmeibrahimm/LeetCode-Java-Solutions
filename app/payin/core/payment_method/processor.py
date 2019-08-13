import logging
from datetime import datetime

from typing import Optional, Any, Tuple

from asyncpg import DataError

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import ReqContext
from app.commons.providers.stripe_models import (
    CreatePaymentMethod,
    AttachPaymentMethod,
    DetachPaymentMethod,
)
from app.commons.types import CountryCode
from app.commons.utils.uuid import generate_object_uuid, ResourceUuidPrefix
from app.payin.core.exceptions import (
    PaymentMethodCreateError,
    PayinErrorCode,
    payin_error_message_maps,
    PaymentMethodReadError,
    PayerReadError,
    PaymentMethodDeleteError,
)

from app.payin.core.payment_method.model import PaymentMethod, Card
from app.payin.core.types import PaymentMethodIdType, PayerIdType
from app.payin.repository.payer_repo import (
    PayerRepository,
    GetPayerByIdInput,
    GetPayerByIdOutput,
)
from app.payin.repository.payment_method_repo import (
    InsertPgpPaymentMethodInput,
    InsertStripeCardInput,
    PgpPaymentMethodDbEntity,
    GetPgpPaymentMethodByPaymentMethodIdInput,
    StripeCardDbEntity,
    GetStripeCardByStripeIdInput,
    GetPgpPaymentMethodByPgpResourceIdInput,
    GetStripeCardByIdInput,
    PaymentMethodRepository,
    DeletePgpPaymentMethodByIdSetInput,
    DeletePgpPaymentMethodByIdWhereInput,
    DeleteStripeCardByIdSetInput,
    DeleteStripeCardByIdWhereInput,
)

logger = logging.getLogger(__name__)


async def create_payment_method_impl(
    payment_method_repository: PaymentMethodRepository,
    app_ctxt: AppContext,
    req_ctxt: ReqContext,
    payer_id: Optional[str],
    payment_gateway: str,
    token: str,
    dd_consumer_id: Optional[str],
    stripe_customer_id: Optional[str],
    country: Optional[str] = CountryCode.US.value,
) -> PaymentMethod:
    """
    Implementation to create a payment method.

    :param payment_method_repository:
    :param app_ctxt: Application context
    :param req_ctxt: Request context
    :param payer_id:
    :param payment_gateway:
    :param token:
    :param dd_consumer_id:
    :param stripe_customer_id:
    :param country:
    :return: PaymentMethod object
    """

    # step 1: lookup stripe_customer_id by payer_id from Payers table if not present
    # TODO: retrieve pgp_resouce_id from pgp_customers table, instead of payers.legacy_stripe_customer_id
    st_cus_id: Optional[str]
    if stripe_customer_id:
        st_cus_id = stripe_customer_id
    elif payer_id or dd_consumer_id:
        payer_repository = PayerRepository(context=app_ctxt)
        payer_entity: Optional[
            GetPayerByIdOutput
        ] = await payer_repository.get_payer_by_id(
            request=(
                GetPayerByIdInput(id=payer_id)
                if payer_id
                else GetPayerByIdInput(dd_payer_id=dd_consumer_id)
            )
        )
        if not payer_entity:
            err_code = PayinErrorCode.PAYER_READ_NOT_FOUND.value
            raise PayerReadError(
                error_code=err_code,
                error_message=payin_error_message_maps[err_code],
                retryable=False,
            )
        st_cus_id = payer_entity.legacy_stripe_customer_id
    else:
        req_ctxt.log.info(
            "[create_payment_method_impl][%s] invalid input. must provide id : %s",
            payer_id,
        )
        err_code = PayinErrorCode.PAYMENT_METHOD_CREATE_INVALID_INPUT.value
        raise PaymentMethodCreateError(
            error_code=err_code,
            error_message=payin_error_message_maps[err_code],
            retryable=False,
        )

    # TODO: perform Payer's lazy creation

    # step 2: create and attach PGP payment_method
    try:
        # create PGP payment method
        stripe_payment_method = await app_ctxt.stripe.create_payment_method(
            country=CountryCode(country),
            request=CreatePaymentMethod(
                type="card", card=CreatePaymentMethod.Card(token=token)
            ),
        )

        # attach PGP payment method
        attach_payment_method = await app_ctxt.stripe.attach_payment_method(
            country=CountryCode(country),
            request=AttachPaymentMethod(
                sid=stripe_payment_method.id, customer=st_cus_id
            ),
        )
        req_ctxt.log.info(
            "[create_payment_method_impl][%s] attach payment_method completed. customer_id from response: %s",
            payer_id,
            attach_payment_method.customer,
        )
        now = datetime.utcnow()
    except Exception as e:
        # req_ctxt.log.error(e)
        # TODO Error logged below does not describe what the error is, meaning log statement cannot be used to diagnose the problem.
        # Add additional details to the log statement and use this convention throughout.
        req_ctxt.log.error(
            "[create_payment_method_impl][{}] error while creating stripe payment method".format(
                payer_id, e
            )
        )
        raise PaymentMethodCreateError(
            error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_STRIPE_ERROR,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYMENT_METHOD_CREATE_STRIPE_ERROR.value
            ],
            retryable=False,
        )
    req_ctxt.log.info(
        "[create_payment_method_impl][%s] create stripe payment_method [%s] completed and attached to customer [%s]",
        payer_id,
        stripe_payment_method.id,
        st_cus_id,
    )

    # FIXME: where do we refer the active flag from
    active: bool = True

    # step 3: crete pgp_payment_method and stripe_card objects
    try:
        pm_entity, sc_entity = await payment_method_repository.insert_payment_method_and_stripe_card(
            pm_input=InsertPgpPaymentMethodInput(
                id=generate_object_uuid(ResourceUuidPrefix.PGP_PAYMENT_METHOD),
                payer_id=(payer_id if payer_id else None),
                pgp_code=payment_gateway,
                pgp_resource_id=stripe_payment_method.id,
                legacy_consumer_id=dd_consumer_id,
                type=stripe_payment_method.type,
                object=stripe_payment_method.object,
                created_at=now,
                updated_at=now,
                attached_at=now,
            ),
            sc_input=InsertStripeCardInput(
                stripe_id=stripe_payment_method.id,
                fingerprint=stripe_payment_method.card.fingerprint,
                last4=stripe_payment_method.card.last4,
                country_of_origin=stripe_payment_method.card.country,
                dynamic_last4=stripe_payment_method.card.last4,
                exp_month=stripe_payment_method.card.exp_month,
                exp_year=stripe_payment_method.card.exp_year,
                type=stripe_payment_method.card.brand,
                active=active,
                created_at=now,
            ),
        )
    except DataError as e:
        req_ctxt.log.error(
            "[update_payer_impl][{}] DataError when read db.".format(payer_id), e
        )
        raise PaymentMethodCreateError(
            error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_DB_ERROR,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYMENT_METHOD_CREATE_DB_ERROR.value
            ],
            retryable=True,
        )

    # TODO step 4: update default_payment_method _id in pgp_customers and stripe_customer tables

    return _build_payment_method(
        pgp_payment_method_entity=pm_entity, stripe_card_entity=sc_entity
    )


async def get_payment_method_impl(
    payment_method_repository: PaymentMethodRepository,
    app_ctxt: AppContext,
    req_ctxt: ReqContext,
    payer_id: str,
    payment_method_id: str,
    payer_id_type: str = None,
    payment_method_id_type: str = None,
    force_update: Optional[bool] = False,
) -> PaymentMethod:
    """
    Implementation to get a payment method.

    :param payment_method_repository:
    :param app_ctxt: Application context
    :param req_ctxt: Request context
    :param payer_id:
    :param payment_method_id:
    :param payer_id_type:
    :param payment_method_id_type:
    :param force_update:
    :return: PaymentMethod object.
    """

    # TODO: step 1: if force_update is true, we should retrieve the payment_method from GPG

    # step 2: retrieve data from DB
    (pm_entity, sc_entity, is_found, is_owner) = await get_payment_method(
        payment_method_repository=payment_method_repository,
        req_ctxt=req_ctxt,
        payer_id=payer_id,
        payment_method_id=payment_method_id,
        payer_id_type=payer_id_type,
        payment_method_id_type=payment_method_id_type,
    )

    if is_found is False:
        req_ctxt.log.error(
            "[get_payment_method_impl][%s] cant retrieve data from pgp_payment_method and stripe_card tables!",
            payment_method_id,
        )
        err_code = PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND.value
        raise PaymentMethodReadError(
            error_code=err_code,
            error_message=payin_error_message_maps[err_code],
            retryable=False,
        )
    if is_owner is False:
        req_ctxt.log.error(
            "[get_payment_method_impl][%s][%s] payer doesn't own payment_method. payer_id_type:[%s] payment_method_id_type:[%s] ",
            payer_id,
            payment_method_id,
            payer_id_type,
            payment_method_id_type,
        )
        raise PaymentMethodCreateError(
            error_code=PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH.value
            ],
            retryable=False,
        )

    # TODO: lazy create payer

    return _build_payment_method(
        pgp_payment_method_entity=pm_entity, stripe_card_entity=sc_entity
    )


async def list_payment_methods_impl(
    payer_id: str, payer_id_type: str = None
) -> PaymentMethod:
    ...


async def delete_payment_method_impl(
    payment_method_repository: PaymentMethodRepository,
    app_ctxt: AppContext,
    req_ctxt: ReqContext,
    payer_id: str,
    payment_method_id: str,
    payer_id_type: str = None,
    payment_method_id_type: str = None,
) -> PaymentMethod:
    """
    Implementation of delete/detach a payment method.

    :param payment_method_repository:
    :param app_ctxt:
    :param req_ctxt:
    :param payer_id:
    :param payment_method_id:
    :param payer_id_type:
    :param payment_method_id_type:
    :return:
    """
    # step 1: find payment_method.
    (pm_entity, sc_entity, is_found, is_owner) = await get_payment_method(
        payment_method_repository=payment_method_repository,
        req_ctxt=req_ctxt,
        payer_id=payer_id,
        payment_method_id=payment_method_id,
        payer_id_type=payer_id_type,
        payment_method_id_type=payment_method_id_type,
    )
    pgp_payment_method_id = (
        pm_entity.pgp_resource_id
        if pm_entity
        else (sc_entity.stripe_id if sc_entity else "")
    )

    # step 2: detach PGP payment method
    try:
        stripe_payment_method = await app_ctxt.stripe.detach_payment_method(
            country=CountryCode("US"),  # TODO: get from payer
            request=DetachPaymentMethod(sid=pgp_payment_method_id),
        )
        req_ctxt.log.info(
            "[delete_payment_method_impl][%s][%s] detach payment method completed. customer in stripe response blob:",
            payer_id,
            payment_method_id,
            stripe_payment_method.customer,
        )
    except Exception as e:
        # req_ctxt.log.error(e)
        # TODO Error logged below does not describe what the error is, meaning log statement cannot be used to diagnose the problem.
        # Add additional details to the log statement and use this convention throughout.
        req_ctxt.log.error(
            "[delete_payment_method_impl][{}] error while detaching stripe payment method".format(
                payer_id, e
            )
        )
        raise PaymentMethodDeleteError(
            error_code=PayinErrorCode.PAYMENT_METHOD_DELETE_STRIPE_ERROR,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYMENT_METHOD_DELETE_STRIPE_ERROR.value
            ],
            retryable=False,
        )

    # step 3: update pgp_payment_method.detached_at
    now = datetime.utcnow()
    try:
        if pm_entity:
            updated_pm_entity = await payment_method_repository.delete_pgp_payment_method_by_id(
                input_set=DeletePgpPaymentMethodByIdSetInput(
                    detached_at=now, deleted_at=now, updated_at=now
                ),
                input_where=DeletePgpPaymentMethodByIdWhereInput(id=pm_entity.id),
            )

        # step 4: update stripe_card.active and remove_at
        if sc_entity:
            updated_sc_entity = await payment_method_repository.delete_stripe_card_by_id(
                input_set=DeleteStripeCardByIdSetInput(removed_at=now),
                input_where=DeleteStripeCardByIdWhereInput(id=sc_entity.id),
            )
    except DataError as e:
        req_ctxt.log.error(
            "[delete_payment_method_impl][{}][{}] DataError when read db.".format(
                payer_id, payment_method_id
            ),
            e,
        )
        raise PaymentMethodDeleteError(
            error_code=PayinErrorCode.PAYMENT_METHOD_DELETE_DB_ERROR,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYMENT_METHOD_DELETE_DB_ERROR.value
            ],
            retryable=True,
        )

    # TODO: step 5: update payer and pgp_customers / stripe_customer to remove the default_payment_method.

    return _build_payment_method(
        pgp_payment_method_entity=updated_pm_entity,
        stripe_card_entity=updated_sc_entity,
    )


async def get_payment_method(
    payment_method_repository: PaymentMethodRepository,
    req_ctxt: ReqContext,
    payer_id: str,
    payment_method_id: str,
    payer_id_type: str = None,
    payment_method_id_type: str = None,
) -> Tuple[
    Optional[PgpPaymentMethodDbEntity], Optional[StripeCardDbEntity], bool, bool
]:
    """
    Utility function to get payment_method.

    :param payment_method_repository: payment method repository.
    :param req_ctxt: request context.
    :param payer_id: DoorDash payer id. For backward compatibility, payer_id can be payer_id,
           stripe_customer_id, or stripe_customer_serial_id
    :param payment_method_id: DoorDash payment method id. For backward compatibility, payment_method_id can
           be either dd_payment_method_id, stripe_payment_method_id, or stripe_card_serial_id
    :param payer_id_type: See: PayerIdType. identify the type of payer_id. Valid values include "dd_payer_id",
           "stripe_customer_id", "stripe_customer_serial_id" (default is "dd_payer_id")
    :param payment_method_id_type: See: PaymentMethodIdType. identify the type of payment_method_id. Valid values
           including "dd_payment_method_id", "stripe_payment_method_id", "stripe_card_serial_id"
           (default is "dd_payment_method_id")
    :return: (PgpPaymentMethodDbEntity, StripeCardDbEntity)
    """
    sc_entity: Optional[StripeCardDbEntity] = None
    pm_entity: Optional[PgpPaymentMethodDbEntity] = None
    is_found: bool = False
    is_owner: bool = False
    try:
        if (
            payment_method_id_type
            == PaymentMethodIdType.PAYMENT_PAYMENT_METHOD_ID.value
        ) or (not payment_method_id_type):
            # get pgp_payment_method object
            pm_entity = await payment_method_repository.get_pgp_payment_method_by_payment_method_id(
                input=GetPgpPaymentMethodByPaymentMethodIdInput(
                    payment_method_id=payment_method_id
                )
            )
            # get stripe_card object
            sc_entity = (
                None
                if not pm_entity
                else await payment_method_repository.get_stripe_card_by_stripe_id(
                    GetStripeCardByStripeIdInput(stripe_id=pm_entity.pgp_resource_id)
                )
            )

            is_found = True if (pm_entity and sc_entity) else False
            if (payer_id_type == PayerIdType.DD_PAYMENT_PAYER_ID.value) or (
                not payer_id_type
            ):
                is_owner = (payer_id == pm_entity.payer_id) if pm_entity else False
            elif payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID:
                is_owner = (
                    (payer_id == pm_entity.pgp_resource_id) if pm_entity else False
                )

        elif (
            payment_method_id_type == PaymentMethodIdType.STRIPE_PAYMENT_METHOD_ID.value
        ):  # DSJ backward compatibility
            # get pgp_payment_method object. Could be None if it's not created through Payin APIs.
            pm_entity = await payment_method_repository.get_pgp_payment_method_by_pgp_resource_id(
                input=GetPgpPaymentMethodByPgpResourceIdInput(
                    pgp_resource_id=payment_method_id
                )
            )
            # get stripe_card object
            sc_entity = await payment_method_repository.get_stripe_card_by_stripe_id(
                GetStripeCardByStripeIdInput(stripe_id=payment_method_id)
            )

            is_found = True if sc_entity else False
            if payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID:
                is_owner = (
                    (payer_id == sc_entity.external_stripe_customer_id)
                    if sc_entity
                    else False
                )

        elif (
            payment_method_id_type == PaymentMethodIdType.STRIPE_CARD_SERIAL_ID.value
        ):  # DSJ backward compatibility
            # get stripe_card object
            sc_entity = await payment_method_repository.get_stripe_card_by_id(
                GetStripeCardByIdInput(id=payment_method_id)
            )
            # get pgp_payment_method object
            pm_entity = (
                None
                if not sc_entity
                else await payment_method_repository.get_pgp_payment_method_by_pgp_resource_id(
                    input=GetPgpPaymentMethodByPgpResourceIdInput(
                        pgp_resource_id=sc_entity.stripe_id
                    )
                )
            )

            is_found = True if sc_entity else False
            if payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID:
                is_owner = (
                    (payer_id == sc_entity.external_stripe_customer_id)
                    if sc_entity
                    else False
                )

        else:
            req_ctxt.log.error(
                "[get_payment_method][%s] invalid payment_method_id_type %s",
                payment_method_id,
                payment_method_id_type,
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE,
                error_message=payin_error_message_maps[
                    PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE.value
                ],
                retryable=False,
            )
    except DataError as e:
        req_ctxt.log.error(
            "[get_payment_method][{}][{}] DataError when read db.".format(
                payer_id, payment_method_id
            ),
            e,
        )
        raise PaymentMethodReadError(
            error_code=PayinErrorCode.PAYMENT_METHOD_GET_DB_ERROR,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYMENT_METHOD_GET_DB_ERROR.value
            ],
            retryable=True,
        )

    if is_found is False:
        req_ctxt.log.error(
            "[get_payment_method][%s] cant retrieve data from pgp_payment_method and stripe_card tables!",
            payment_method_id,
        )
        err_code = PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND.value
        raise PaymentMethodReadError(
            error_code=err_code,
            error_message=payin_error_message_maps[err_code],
            retryable=False,
        )
    if is_owner is False:
        req_ctxt.log.error(
            "[get_payment_method][%s][%s] payer doesn't own payment_method. payer_id_type:[%s] payment_method_id_type:[%s] ",
            payment_method_id,
            payer_id,
            payer_id_type,
            payment_method_id_type,
        )
        raise PaymentMethodReadError(
            error_code=PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH.value
            ],
            retryable=False,
        )

    req_ctxt.log.info(
        "[get_payment_method][%s][%s] find payment_method!!",
        payment_method_id,
        payer_id,
    )

    return (pm_entity, sc_entity, is_found, is_owner)


def _build_payment_method(
    pgp_payment_method_entity: Optional[PgpPaymentMethodDbEntity],
    stripe_card_entity: Any,  # StripeCardDbEntity
) -> PaymentMethod:
    """
    Build PaymentMethod object.

    :param pgp_payment_method_entity: pgp_payment_method_entity returned from pgp_payment_method. It could
           be None if the payment_method was not created through payin APIs.
    :param stripe_card_entity:
    :return: PaymentMethod object
    """

    card: Card = Card(
        country=stripe_card_entity.country_of_origin,
        last4=stripe_card_entity.last4,
        exp_year=stripe_card_entity.exp_year,
        exp_month=stripe_card_entity.exp_month,
        fingerprint=stripe_card_entity.fingerprint,
        active=stripe_card_entity.active,
        brand=stripe_card_entity.type,
        payment_provider_card_id=stripe_card_entity.stripe_id,
    )
    return (
        PaymentMethod(
            id=pgp_payment_method_entity.id,
            payer_id=pgp_payment_method_entity.payer_id,
            dd_consumer_id=pgp_payment_method_entity.legacy_consumer_id,
            payment_provider=pgp_payment_method_entity.pgp_code,
            type=pgp_payment_method_entity.type,
            card=card,
            created_at=pgp_payment_method_entity.created_at,
            updated_at=pgp_payment_method_entity.updated_at,
            deleted_at=pgp_payment_method_entity.deleted_at,
        )
        if pgp_payment_method_entity
        else PaymentMethod(
            id=stripe_card_entity.id,
            dd_consumer_id=str(stripe_card_entity.consumer_id),
            payment_provider="stripe",
            type="card",
            card=card,
            created_at=stripe_card_entity.created_at,
            deleted_at=stripe_card_entity.removed_at,
            payer_id=None,
            payment_provider_customer_id=None,
            updated_at=None,
        )
    )
