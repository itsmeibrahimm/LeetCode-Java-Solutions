from abc import abstractmethod
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import Depends
from psycopg2._psycopg import DataError
from structlog.stdlib import BoundLogger

from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import (
    get_logger_from_req,
    get_stripe_async_client_from_req,
)
from app.commons import tracing
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import (
    StripeCreatePaymentMethodRequest,
    StripeAttachPaymentMethodRequest,
    StripeDetachPaymentMethodRequest,
)
from app.commons.providers.stripe.stripe_models import (
    PaymentMethod as StripePaymentMethod,
)
from app.commons.types import CountryCode
from app.payin.core.exceptions import (
    PaymentMethodCreateError,
    PayinErrorCode,
    PaymentMethodReadError,
    PaymentMethodDeleteError,
)
from app.payin.core.payment_method.model import RawPaymentMethod
from app.payin.core.types import PaymentMethodIdType, PayerIdType, MixedUuidStrType

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
    GetStripeCardsByStripeCustomerIdInput,
    GetStripeCardsByConsumerIdInput,
    GetDuplicateStripeCardInput,
)


@tracing.track_breadcrumb(processor_name="payment_methods")
class PaymentMethodClient:
    """
    PaymentMethod client wrapper that provides utilities to PaymentMethod.
    """

    def __init__(
        self,
        payment_method_repo: PaymentMethodRepository = Depends(
            PaymentMethodRepository.get_repository
        ),
        log: BoundLogger = Depends(get_logger_from_req),
        app_ctxt: AppContext = Depends(get_global_app_context),
        stripe_async_client: StripeAsyncClient = Depends(
            get_stripe_async_client_from_req
        ),
    ):
        self.payment_method_repo = payment_method_repo
        self.log = log
        self.app_ctxt = app_ctxt
        self.stripe_async_client = stripe_async_client

    async def create_raw_payment_method(
        self,
        id: UUID,
        pgp_code: str,
        stripe_payment_method: StripePaymentMethod,
        payer_id: Optional[str],
        legacy_consumer_id: Optional[str] = None,
    ) -> RawPaymentMethod:
        now = datetime.utcnow()
        try:
            dynamic_last4: Optional[str] = None
            tokenization_method: Optional[str] = None
            if stripe_payment_method.card.wallet:
                dynamic_last4 = stripe_payment_method.card.wallet.dynamic_last4
                tokenization_method = stripe_payment_method.card.wallet.type

            pm_entity = await self.payment_method_repo.insert_pgp_payment_method(
                pm_input=InsertPgpPaymentMethodInput(
                    id=id,
                    payer_id=(payer_id if payer_id else None),
                    pgp_code=pgp_code,
                    pgp_resource_id=stripe_payment_method.id,
                    legacy_consumer_id=legacy_consumer_id,
                    type=stripe_payment_method.type,
                    object=stripe_payment_method.object,
                    created_at=now,
                    updated_at=now,
                    attached_at=now,
                )
            )

            sc_entity = await self.payment_method_repo.insert_stripe_card(
                sc_input=InsertStripeCardInput(
                    stripe_id=stripe_payment_method.id,
                    fingerprint=stripe_payment_method.card.fingerprint,
                    last4=stripe_payment_method.card.last4 or "",
                    external_stripe_customer_id=stripe_payment_method.customer,
                    country_of_origin=stripe_payment_method.card.country,
                    dynamic_last4=dynamic_last4 or "",
                    tokenization_method=tokenization_method,
                    exp_month=str(stripe_payment_method.card.exp_month).zfill(2),
                    exp_year=str(stripe_payment_method.card.exp_year).zfill(4),
                    type=stripe_payment_method.card.brand,
                    active=True,
                    consumer_id=(
                        int(legacy_consumer_id) if legacy_consumer_id else None
                    ),
                    zip_code=stripe_payment_method.billing_details.address.postal_code,
                    address_line1_check=stripe_payment_method.card.checks.address_line1_check,
                    address_zip_check=stripe_payment_method.card.checks.address_postal_code_check,
                    created_at=now,  # FIXME: need to fix timezone
                )
            )

            # TODO: add new state in pgp_payment_methods table to keep track of cross DB consistency

        except DataError as e:
            self.log.error(
                f"[create_raw_payment_method][{payer_id}] DataError when write db. {e}"
            )
            raise PaymentMethodCreateError(
                error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_DB_ERROR, retryable=True
            )
        return RawPaymentMethod(
            pgp_payment_method_entity=pm_entity, stripe_card_entity=sc_entity
        )

    async def _get_raw_payment_method(
        self,
        payment_method_id: MixedUuidStrType,
        payer_id: Optional[MixedUuidStrType] = None,
        payer_id_type: Optional[str] = None,
        payment_method_id_type: Optional[str] = None,
    ) -> RawPaymentMethod:
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

        pm_interface: PaymentMethodOpsInterface
        if (payment_method_id_type == PaymentMethodIdType.PAYMENT_METHOD_ID) or (
            not payment_method_id_type
        ):
            pm_interface = PaymentMethodOps(
                log=self.log, payment_method_repo=self.payment_method_repo
            )
        elif payment_method_id_type in (
            PaymentMethodIdType.STRIPE_PAYMENT_METHOD_ID,
            PaymentMethodIdType.DD_STRIPE_CARD_ID,
        ):
            pm_interface = LegacyPaymentMethodOps(
                log=self.log, payment_method_repo=self.payment_method_repo
            )
        else:
            self.log.warn(
                f"[_get_payment_method][{payment_method_id}] invalid payment_method_id_type {payment_method_id_type}"
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE,
                retryable=False,
            )

        raw_payment_method: RawPaymentMethod = await pm_interface.get_payment_method_raw_objects(
            payer_id=payer_id,
            payment_method_id=payment_method_id,
            payer_id_type=payer_id_type,
            payment_method_id_type=payment_method_id_type,
        )

        self.log.info(
            f"[_get_payment_method][{payment_method_id}][{payer_id}] find payment_method!!"
        )
        return raw_payment_method

    async def get_raw_payment_method(
        self,
        payer_id: MixedUuidStrType,
        payment_method_id: MixedUuidStrType,
        payer_id_type: Optional[str] = None,
        payment_method_id_type: Optional[str] = None,
    ) -> RawPaymentMethod:

        return await self._get_raw_payment_method(
            payment_method_id=payment_method_id,
            payer_id=payer_id,
            payer_id_type=payer_id_type,
            payment_method_id_type=payment_method_id_type,
        )

    async def get_raw_payment_method_without_payer_auth(
        self,
        payment_method_id: MixedUuidStrType,
        payment_method_id_type: Optional[str] = None,
    ) -> RawPaymentMethod:

        return await self._get_raw_payment_method(
            payment_method_id=payment_method_id,
            payment_method_id_type=payment_method_id_type,
        )

    async def get_duplicate_payment_method(
        self,
        stripe_payment_method: StripePaymentMethod,
        dd_consumer_id: str,
        pgp_customer_resource_id: str,
    ) -> RawPaymentMethod:
        try:
            dynamic_last4: Optional[str] = None
            if stripe_payment_method.card.wallet:
                dynamic_last4 = stripe_payment_method.card.wallet.dynamic_last4

            # get stripe_card object
            sc_entity = await self.payment_method_repo.get_duplicate_stripe_card(
                input=GetDuplicateStripeCardInput(
                    fingerprint=stripe_payment_method.card.fingerprint,
                    dynamic_last4=dynamic_last4 or "",
                    exp_year=str(stripe_payment_method.card.exp_year).zfill(4),
                    exp_month=str(stripe_payment_method.card.exp_month).zfill(2),
                    external_stripe_customer_id=pgp_customer_resource_id,
                    # consumer_id=str(dd_consumer_id),
                    active=True,
                )
            )
            if not sc_entity:
                raise PaymentMethodReadError(
                    error_code=PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND,
                    retryable=False,
                )

            # get pgp_payment_method object
            pm_entity = await self.payment_method_repo.get_pgp_payment_method_by_pgp_resource_id(
                input=GetPgpPaymentMethodByPgpResourceIdInput(
                    pgp_resource_id=sc_entity.stripe_id
                )
            )

            return RawPaymentMethod(
                pgp_payment_method_entity=pm_entity, stripe_card_entity=sc_entity
            )
        except DataError as e:
            self.log.exception(
                f"[get_duplicate_payment_method][{stripe_payment_method.id}] DataError when read db: {e}"
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_DB_ERROR, retryable=True
            )

    async def detach_raw_payment_method(
        self, pgp_payment_method_id: str, raw_payment_method: RawPaymentMethod
    ) -> RawPaymentMethod:
        updated_pm_entity: Optional[PgpPaymentMethodDbEntity] = None
        updated_sc_entity: Optional[StripeCardDbEntity] = None
        try:
            now = datetime.utcnow()
            if raw_payment_method.pgp_payment_method_entity:
                updated_pm_entity = await self.payment_method_repo.delete_pgp_payment_method_by_id(
                    input_set=DeletePgpPaymentMethodByIdSetInput(
                        detached_at=now, deleted_at=now, updated_at=now
                    ),
                    input_where=DeletePgpPaymentMethodByIdWhereInput(
                        id=raw_payment_method.pgp_payment_method_entity.id
                    ),
                )

            if raw_payment_method.stripe_card_entity:
                updated_sc_entity = await self.payment_method_repo.delete_stripe_card_by_id(
                    input_set=DeleteStripeCardByIdSetInput(
                        removed_at=now, active=False
                    ),
                    input_where=DeleteStripeCardByIdWhereInput(
                        id=raw_payment_method.stripe_card_entity.id
                    ),
                )
        except DataError as e:
            self.log.error(
                f"[detach_payment_method][{pgp_payment_method_id}] DataError when read db. {e}"
            )
            raise PaymentMethodDeleteError(
                error_code=PayinErrorCode.PAYMENT_METHOD_DELETE_DB_ERROR, retryable=True
            )
        return RawPaymentMethod(
            pgp_payment_method_entity=updated_pm_entity,
            stripe_card_entity=updated_sc_entity,
        )

    async def pgp_create_payment_method(
        self, token: str, country: Optional[str] = CountryCode.US
    ) -> StripePaymentMethod:
        try:
            stripe_payment_method = await self.stripe_async_client.create_payment_method(
                country=CountryCode(country),
                request=StripeCreatePaymentMethodRequest(
                    type="card", card=StripeCreatePaymentMethodRequest.Card(token=token)
                ),
            )

            self.log.info(
                "[pgp_create_and_attach_payment_method] create payment_method completed.",
                pgp_payment_method_res_id=stripe_payment_method.id,
            )
        except Exception as e:
            self.log.error(
                f"[create_payment_method_impl]error while creating stripe payment method. {e}"
            )
            raise PaymentMethodCreateError(
                error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_STRIPE_ERROR,
                retryable=False,
            )
        return stripe_payment_method

    async def pgp_attach_payment_method(
        self, pgp_payment_method_res_id: str, pgp_customer_id: str, country: str
    ) -> StripePaymentMethod:
        try:
            attach_payment_method = await self.stripe_async_client.attach_payment_method(
                country=CountryCode(country),
                request=StripeAttachPaymentMethodRequest(
                    sid=pgp_payment_method_res_id, customer=pgp_customer_id
                ),
            )
            self.log.info(
                f"[pgp_create_and_attach_payment_method][{pgp_customer_id}] attach payment_method completed. customer_id from response:{attach_payment_method.customer}"
            )
        except Exception as e:
            self.log.error(
                f"[create_payment_method_impl][{pgp_customer_id}] error while creating stripe payment method. {e}"
            )
            raise PaymentMethodCreateError(
                error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_STRIPE_ERROR,
                retryable=False,
            )
        return attach_payment_method

    async def pgp_detach_payment_method(
        self, pgp_payment_method_id: str, country: str
    ) -> StripePaymentMethod:
        try:
            stripe_payment_method = await self.stripe_async_client.detach_payment_method(
                country=CountryCode(country),  # TODO: get from payer
                request=StripeDetachPaymentMethodRequest(sid=pgp_payment_method_id),
            )
            self.log.info(
                f"[pgp_detach_payment_method][{pgp_payment_method_id}] detach payment method completed. customer in stripe response blob:"
            )
        except Exception as e:
            self.log.error(
                f"[pgp_detach_payment_method][{pgp_payment_method_id}] error while detaching stripe payment method {e}"
            )
            raise PaymentMethodDeleteError(
                error_code=PayinErrorCode.PAYMENT_METHOD_DELETE_STRIPE_ERROR,
                retryable=False,
            )
        return stripe_payment_method

    async def get_dd_stripe_card_ids_by_stripe_customer_id(
        self, stripe_customer_id: str
    ):
        try:
            stripe_customer_db_entities = await self.payment_method_repo.get_dd_stripe_card_ids_by_stripe_customer_id(
                input=GetStripeCardsByStripeCustomerIdInput(
                    stripe_customer_id=stripe_customer_id
                )
            )
        except DataError as e:
            self.log.error(
                f"[get_dd_stripe_card_ids_by_stripe_customer_id][{stripe_customer_id}]DataError when read db: {e}"
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_DB_ERROR, retryable=True
            )
        stripe_card_ids = [entity.id for entity in stripe_customer_db_entities]
        return stripe_card_ids

    async def get_stripe_card_ids_for_consumer_id(self, consumer_id: int):
        stripe_card_db_entities = await self.payment_method_repo.get_stripe_cards_by_consumer_id(
            input=GetStripeCardsByConsumerIdInput(consumer_id=consumer_id)
        )
        return [entity.id for entity in stripe_card_db_entities]


class PaymentMethodOpsInterface:
    def __init__(self, log: BoundLogger, payment_method_repo: PaymentMethodRepository):
        self.log = log
        self.payment_method_repo = payment_method_repo

    @abstractmethod
    async def get_payment_method_raw_objects(
        self,
        payment_method_id: MixedUuidStrType,
        payer_id: Optional[MixedUuidStrType],
        payer_id_type: Optional[str],
        payment_method_id_type: Optional[str],
    ) -> RawPaymentMethod:
        pass


class PaymentMethodOps(PaymentMethodOpsInterface):
    async def get_payment_method_raw_objects(
        self,
        payment_method_id: MixedUuidStrType,
        payer_id: Optional[MixedUuidStrType],
        payer_id_type: Optional[str],
        payment_method_id_type: Optional[str],
    ) -> RawPaymentMethod:
        sc_entity: Optional[StripeCardDbEntity] = None
        pm_entity: Optional[PgpPaymentMethodDbEntity] = None
        try:
            # get pgp_payment_method object
            pm_entity = await self.payment_method_repo.get_pgp_payment_method_by_payment_method_id(
                input=GetPgpPaymentMethodByPaymentMethodIdInput(
                    payment_method_id=payment_method_id
                )
            )
            # get stripe_card object
            if pm_entity:
                sc_entity = await self.payment_method_repo.get_stripe_card_by_stripe_id(
                    GetStripeCardByStripeIdInput(stripe_id=pm_entity.pgp_resource_id)
                )
        except DataError as e:
            self.log.error(
                f"[get_payment_method_raw_objects][{payer_id}][{payment_method_id}] DataError when read db: {e}"
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_DB_ERROR, retryable=True
            )

        if not (pm_entity and sc_entity):
            self.log.error(
                "[get_payment_method_raw_objects][{payment_method_id}] cant retrieve data from pgp_payment_method and stripe_card tables!"
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND, retryable=False
            )

        is_owner: bool = False
        if not payer_id:
            # no need to authorize payment_method
            is_owner = True
        else:
            if (payer_id_type == PayerIdType.PAYER_ID) or (not payer_id_type):
                if pm_entity:
                    is_owner = payer_id == pm_entity.payer_id
            elif payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID:
                is_owner = payer_id == sc_entity.external_stripe_customer_id
        if is_owner is False:
            self.log.warn(
                "[get_payment_method_raw_objects][%s][%s] payer doesn't own payment_method. payer_id_type:[%s] payment_method_id_type:[%s] ",
                payment_method_id,
                payer_id,
                payer_id_type,
                payment_method_id_type,
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH,
                retryable=False,
            )

        self.log.info(
            f"[get_payment_method_raw_objects][{payment_method_id}][{payer_id}] find payment_method!"
        )
        return RawPaymentMethod(
            pgp_payment_method_entity=pm_entity, stripe_card_entity=sc_entity
        )


class LegacyPaymentMethodOps(PaymentMethodOpsInterface):
    async def get_payment_method_raw_objects(
        self,
        payment_method_id: MixedUuidStrType,
        payer_id: Optional[MixedUuidStrType],
        payer_id_type: Optional[str],
        payment_method_id_type: Optional[str],
    ) -> RawPaymentMethod:
        resp_sc_entity: StripeCardDbEntity  # hate this way, temporarily solution to get rid of compilation error
        sc_entity: Optional[StripeCardDbEntity] = None
        pm_entity: Optional[PgpPaymentMethodDbEntity] = None
        try:
            if payment_method_id_type == PaymentMethodIdType.STRIPE_PAYMENT_METHOD_ID:
                # get pgp_payment_method object. Could be None if it's not created through Payin APIs.
                pm_entity = await self.payment_method_repo.get_pgp_payment_method_by_pgp_resource_id(
                    input=GetPgpPaymentMethodByPgpResourceIdInput(
                        pgp_resource_id=payment_method_id
                    )
                )
                # get stripe_card object
                sc_entity = await self.payment_method_repo.get_stripe_card_by_stripe_id(
                    GetStripeCardByStripeIdInput(stripe_id=payment_method_id)
                )

            elif payment_method_id_type == PaymentMethodIdType.DD_STRIPE_CARD_ID:
                # get stripe_card object
                sc_entity = await self.payment_method_repo.get_stripe_card_by_id(
                    GetStripeCardByIdInput(id=int(payment_method_id))
                )
                # get pgp_payment_method object
                if sc_entity:
                    pm_entity = await self.payment_method_repo.get_pgp_payment_method_by_pgp_resource_id(
                        input=GetPgpPaymentMethodByPgpResourceIdInput(
                            pgp_resource_id=sc_entity.stripe_id
                        )
                    )
            else:
                self.log.error(
                    f"[get_payment_method_raw_objects][{payment_method_id}] invalid payment_method_id_type {payment_method_id_type}"
                )
                raise PaymentMethodReadError(
                    error_code=PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE,
                    retryable=False,
                )
        except DataError as e:
            self.log.error(
                f"[get_payment_method_raw_objects][{payer_id}][{payment_method_id}] DataError when read db: {e}"
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_DB_ERROR, retryable=True
            )

        if not sc_entity:
            self.log.error(
                "[get_payment_method_raw_objects] cant retrieve data from pgp_payment_method and stripe_card tables!",
                payment_method_id=payment_method_id,
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND, retryable=False
            )

        is_owner: bool = False
        if not payer_id:
            # no need to authorize payment_method
            is_owner = True
        else:
            if payer_id_type is None and pm_entity:
                is_owner = payer_id == pm_entity.payer_id
            elif payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID and sc_entity:
                is_owner = payer_id == sc_entity.external_stripe_customer_id
        if is_owner is False:
            self.log.warn(
                f"[get_payment_method_raw_objects][{payment_method_id}][{payer_id}] payer doesn't own payment_method. payer_id_type:[{payer_id_type}] payment_method_id_type:[{payment_method_id_type}] "
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH,
                retryable=False,
            )

        self.log.info(
            "[get_payment_method_raw_objects] find payment_method!",
            payment_method_id=payment_method_id,
            payer_id=payer_id,
        )

        return RawPaymentMethod(
            pgp_payment_method_entity=pm_entity, stripe_card_entity=sc_entity
        )
