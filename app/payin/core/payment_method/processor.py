import logging

from typing import Optional, Any

from asyncpg import DataError

from app.commons.utils.uuid import generate_object_uuid, ResourceUuidPrefix
from app.payin.core.exceptions import (
    PaymentMethodCreateError,
    PayinErrorCode,
    payin_error_message_maps,
    PaymentMethodReadError,
)
from app.payin.core.payment_method.model import PaymentMethod, Card
from app.payin.core.types import PaymentMethodIdType
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
)

logger = logging.getLogger(__name__)


async def create_payment_method_impl(
    payment_method_repository: PaymentMethodRepository,
    payer_id: Optional[str],
    payment_gateway: str,
    token: str,
    dd_consumer_id: Optional[str],
    stripe_customer_id: Optional[str],
) -> PaymentMethod:
    """
    Implementation to create a payment method.

    :param payment_method_repository:
    :param payer_id:
    :param payment_gateway:
    :param token:
    :param dd_consumer_id:
    :param stripe_customer_id:
    :return: PaymentMethod object
    """

    # TODO: step 1: create PGP payment_method
    pgp_resource_id: str = "pm_" + generate_object_uuid()
    fingerprint: str = "i am fingerprint"
    last4: str = "1234"
    dynamic_last4: str = "1233"
    exp_month: str = "11"
    exp_year: str = "1911"
    ttt: str = "visa"
    active: bool = True

    # TODO: perform Payer's lazy creation

    # TODO: step 2: attach the payment method to PGP customer

    # step 3: crete gpg_payment_method and stripe_card objects
    try:
        pm_entity, sc_entity = await payment_method_repository.insert_payment_method_and_stripe_card(
            pm_input=InsertPgpPaymentMethodInput(
                id=generate_object_uuid(ResourceUuidPrefix.PGP_PAYMENT_METHOD),
                payer_id=(payer_id if payer_id else None),
                pgp_code=payment_gateway,
                pgp_resource_id=pgp_resource_id,
                legacy_consumer_id=dd_consumer_id,
            ),
            sc_input=InsertStripeCardInput(
                stripe_id=pgp_resource_id,
                fingerprint=fingerprint,
                last4=last4,
                dynamic_last4=dynamic_last4,
                exp_month=exp_month,
                exp_year=exp_year,
                type=ttt,
                active=active,
            ),
        )
    except DataError as e:
        logger.error(
            "[update_payer_impl][{}] DataError when read db.".format(payer_id), e
        )
        raise PaymentMethodCreateError(
            error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_DB_ERROR,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYMENT_METHOD_CREATE_DB_ERROR.value
            ],
            retryable=True,
        )

    # TODO step 4: determine to update default_payment_method _id in pgp_customers and stripe_customer tables

    return _build_payment_method(
        pgp_payment_method_entity=pm_entity, stripe_card_entity=sc_entity
    )


async def get_payment_method_impl(
    payment_method_repository: PaymentMethodRepository,
    payer_id: str,
    payment_method_id: str,
    payer_id_type: str = None,
    payment_method_id_type: str = None,
    force_update: bool = None,
) -> PaymentMethod:
    """
    Implementation to get a payment method.

    :param payment_method_repository:
    :param payer_id:
    :param payment_method_id:
    :param payer_id_type:
    :param payment_method_id_type:
    :param force_update:
    :return: PaymentMethod object.
    """

    # TODO: if force_update is true, we should retrieve the payment_method from GPG

    # step 2: retrieve data from DB
    sc_entity: Optional[StripeCardDbEntity] = None
    pm_entity: Optional[PgpPaymentMethodDbEntity] = None
    not_found: bool = True
    if (
        payment_method_id_type == PaymentMethodIdType.DD_PAYMENT_PAYMENT_METHOD_ID.value
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
        not_found = True if (pm_entity and sc_entity) else False
    elif payment_method_id_type == PaymentMethodIdType.STRIPE_PAYMENT_METHOD_ID.value:
        # get pgp_payment_method object
        pm_entity = await payment_method_repository.get_pgp_payment_method_by_pgp_resource_id(
            input=GetPgpPaymentMethodByPgpResourceIdInput(
                pgp_resource_id=payment_method_id
            )
        )
        # get stripe_card object
        sc_entity = await payment_method_repository.get_stripe_card_by_stripe_id(
            GetStripeCardByStripeIdInput(stripe_id=payment_method_id)
        )
        not_found = True if sc_entity else False
    elif payment_method_id_type == PaymentMethodIdType.STRIPE_CARD_SERIAL_ID.value:
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
        not_found = True if sc_entity else False
    else:
        logger.error(
            "[get_payment_method_impl][%s] invalid payment_method_id_type %s",
            payment_method_id,
            payment_method_id_type,
        )
        raise PaymentMethodCreateError(
            error_code=PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE.value
            ],
            retryable=False,
        )

    if not_found is False:
        logger.error(
            "[get_payment_method_impl][%s] cant retrieve data from pgp_payment_method and stripe_card tables!",
            payment_method_id,
        )
        err_code = PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND.value
        raise PaymentMethodReadError(
            error_code=err_code,
            error_message=payin_error_message_maps[err_code],
            retryable=False,
        )

    # TODO: verify if payer actually owns this payment method
    # TODO: lazy create payer

    return _build_payment_method(
        pgp_payment_method_entity=pm_entity, stripe_card_entity=sc_entity
    )


async def list_payment_methods_impl(
    payer_id: str, payer_id_type: str = None
) -> PaymentMethod:
    ...


async def delete_payment_method_impl(
    payer_id: str,
    payment_method_id: str,
    payer_id_type: str = None,
    payment_method_object_type: str = None,
) -> PaymentMethod:
    ...


def _build_payment_method(
    pgp_payment_method_entity: Optional[PgpPaymentMethodDbEntity],
    stripe_card_entity: Any,  # StripeCardDbEntity
) -> PaymentMethod:
    """
    Build PaymentMethod object.

    :param pgp_payment_method_entity: pgp_payment_method_entity returned from pgp_payment_method. It could be None if the payment_method was not created through payin APIs.
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
