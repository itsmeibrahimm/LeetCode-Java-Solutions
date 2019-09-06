from abc import abstractmethod
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import Depends
from psycopg2._psycopg import DataError
from structlog.stdlib import BoundLogger

from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import get_logger_from_req
from app.commons import tracing
from app.commons.providers.stripe.stripe_models import (
    CreatePaymentMethod,
    AttachPaymentMethod,
    DetachPaymentMethod,
)
from app.commons.providers.stripe.stripe_models import (
    PaymentMethod as StripePaymentMethod,
)
from app.commons.types import CountryCode
from app.commons.utils.uuid import generate_object_uuid
from app.payin.core.exceptions import (
    PaymentMethodCreateError,
    PayinErrorCode,
    PaymentMethodReadError,
    PaymentMethodDeleteError,
    PayerReadError,
)
from app.payin.core.payer.model import RawPayer
from app.payin.core.payment_method.model import PaymentMethod, RawPaymentMethod
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
    ):
        self.payment_method_repo = payment_method_repo
        self.log = log
        self.app_ctxt = app_ctxt

    async def create_raw_payment_method(
        self,
        id: UUID,
        pgp_code: str,
        stripe_payment_method: StripePaymentMethod,
        payer_id: Optional[str],
        legacy_consumer_id: Optional[str],
    ) -> RawPaymentMethod:
        now = datetime.utcnow()
        try:
            dynamic_last4: Optional[
                str
            ] = ""  # stupid existing DSJ logic in add_payment_card_to_consumer()
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
                    last4=stripe_payment_method.card.last4,
                    external_stripe_customer_id=stripe_payment_method.customer,
                    country_of_origin=stripe_payment_method.card.country,
                    dynamic_last4=dynamic_last4,
                    tokenization_method=tokenization_method,
                    exp_month=stripe_payment_method.card.exp_month,
                    exp_year=stripe_payment_method.card.exp_year,
                    type=stripe_payment_method.card.brand,
                    active=True,
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
        if (payment_method_id_type == PaymentMethodIdType.DD_PAYMENT_METHOD_ID) or (
            not payment_method_id_type
        ):
            pm_interface = PaymentMethodOps(
                log=self.log, payment_method_repo=self.payment_method_repo
            )
        elif payment_method_id_type in (
            PaymentMethodIdType.STRIPE_PAYMENT_METHOD_ID,
            PaymentMethodIdType.DD_STRIPE_CARD_SERIAL_ID,
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

    async def get_raw_payment_method_no_payer_auth(
        self, payment_method_id: str, payment_method_id_type: Optional[str] = None
    ) -> RawPaymentMethod:

        return await self._get_raw_payment_method(
            payment_method_id=payment_method_id,
            payment_method_id_type=payment_method_id_type,
        )

    async def detach_raw_payment_method(
        self,
        payer_id: MixedUuidStrType,
        pgp_payment_method_id: str,
        raw_payment_method: RawPaymentMethod,
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
                        removed_at=now
                    ),  # FIXME: timezone
                    input_where=DeleteStripeCardByIdWhereInput(
                        id=raw_payment_method.stripe_card_entity.id
                    ),
                )
        except DataError as e:
            self.log.error(
                f"[detach_payment_method][{payer_id}][{pgp_payment_method_id}] DataError when read db. {e}"
            )
            raise PaymentMethodDeleteError(
                error_code=PayinErrorCode.PAYMENT_METHOD_DELETE_DB_ERROR, retryable=True
            )
        return RawPaymentMethod(
            pgp_payment_method_entity=updated_pm_entity,
            stripe_card_entity=updated_sc_entity,
        )

    async def pgp_create_and_attach_payment_method(
        self,
        token: str,
        pgp_customer_id: str,
        country: Optional[str] = CountryCode.US,
        attached: Optional[bool] = True,
    ) -> StripePaymentMethod:
        try:
            # create PGP payment method
            stripe_payment_method = await self.app_ctxt.stripe.create_payment_method(
                country=CountryCode(country),
                request=CreatePaymentMethod(
                    type="card", card=CreatePaymentMethod.Card(token=token)
                ),
            )

            # attach PGP payment method
            if attached:
                attach_payment_method = await self.app_ctxt.stripe.attach_payment_method(
                    country=CountryCode(country),
                    request=AttachPaymentMethod(
                        sid=stripe_payment_method.id, customer=pgp_customer_id
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
        self,
        payer_id: MixedUuidStrType,
        pgp_payment_method_id: str,
        country: Optional[str] = CountryCode.US,
    ) -> StripePaymentMethod:
        try:
            stripe_payment_method = await self.app_ctxt.stripe.detach_payment_method(
                country=CountryCode(country),  # TODO: get from payer
                request=DetachPaymentMethod(sid=pgp_payment_method_id),
            )
            self.log.info(
                "[pgp_detach_payment_method][%s][%s] detach payment method completed. customer in stripe response blob:",
                payer_id,
                pgp_payment_method_id,
            )
        except Exception as e:
            self.log.error(
                f"[pgp_detach_payment_method][{payer_id}] error while detaching stripe payment method {e}"
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


class PaymentMethodProcessor:
    """
    External class that is ingested by API presentation layer.
    """

    # prevent circular dependency
    from app.payin.core.payer.processor import PayerClient

    def __init__(
        self,
        log: BoundLogger = Depends(get_logger_from_req),
        app_ctxt: AppContext = Depends(get_global_app_context),
        payment_method_client=Depends(PaymentMethodClient),
        payer_client=Depends(PayerClient),
    ):
        self.log = log
        self.app_ctxt = app_ctxt
        self.payment_method_client = payment_method_client
        self.payer_client = payer_client

    async def create_payment_method(
        self,
        pgp_code: str,
        token: str,
        payer_id: Optional[str],
        dd_consumer_id: Optional[str],
        stripe_customer_id: Optional[str],
        country: Optional[CountryCode] = CountryCode.US,
    ) -> PaymentMethod:
        """
        Implementation to create a payment method.

        :param pgp_code:
        :param token:
        :param payer_id:
        :param dd_consumer_id:
        :param stripe_customer_id:
        :param country:
        :return:
        """

        # step 1: lookup stripe_customer_id by payer_id from Payers table if not present
        # TODO: retrieve pgp_resouce_id from pgp_customers table, instead of payers.legacy_stripe_customer_id
        if not (payer_id or dd_consumer_id or stripe_customer_id):
            self.log.info(f"[create_payment_method] invalid input. must provide id")
            raise PaymentMethodCreateError(
                error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_INVALID_INPUT,
                retryable=False,
            )

        pgp_customer_id: Optional[str]
        if stripe_customer_id:
            pgp_customer_id = stripe_customer_id
        else:
            raw_payer: RawPayer
            if payer_id:
                raw_payer = await self.payer_client.get_raw_payer(
                    payer_id, PayerIdType.DD_PAYMENT_PAYER_ID
                )
            else:
                raw_payer = await self.payer_client.get_raw_payer(
                    dd_consumer_id, PayerIdType.DD_CONSUMER_ID
                )
            pgp_customer_id = raw_payer.pgp_customer_id()

        # TODO: perform Payer's lazy creation

        # step 2: create and attach PGP payment_method
        stripe_payment_method: StripePaymentMethod = await self.payment_method_client.pgp_create_and_attach_payment_method(
            token=token, pgp_customer_id=pgp_customer_id, country=country, attached=True
        )

        self.log.info(
            f"[create_payment_method][{payer_id}] create stripe payment_method [{stripe_payment_method.id}] completed and attached to customer [{pgp_customer_id}]"
        )

        # step 3: crete pgp_payment_method and stripe_card objects
        raw_payment_method: RawPaymentMethod = await self.payment_method_client.create_raw_payment_method(
            id=generate_object_uuid(),
            pgp_code=pgp_code,
            stripe_payment_method=stripe_payment_method,
            payer_id=payer_id,
            legacy_consumer_id=dd_consumer_id,
        )
        return raw_payment_method.to_payment_method()

    async def get_payment_method(
        self,
        payer_id: MixedUuidStrType,
        payment_method_id: str,
        payer_id_type: str = None,
        payment_method_id_type: str = None,
        country: Optional[str] = None,
        force_update: Optional[bool] = False,
    ) -> PaymentMethod:
        """
        Implementation of get payment method

        :param payer_id:
        :param payment_method_id:
        :param payer_id_type:
        :param payment_method_id_type:
        :param country:
        :param force_update:
        :return: PaymentMethod object.
        """

        # TODO: step 1: if force_update is true, we should retrieve the payment_method from GPG

        # step 2: retrieve data from DB
        raw_payment_method: RawPaymentMethod = await self.payment_method_client.get_raw_payment_method(
            payment_method_id=payment_method_id,
            payer_id=payer_id,
            payer_id_type=payer_id_type,
            payment_method_id_type=payment_method_id_type,
        )

        return raw_payment_method.to_payment_method()

    async def list_payment_methods(
        self, payer_id: str, payer_id_type: str = None
    ) -> PaymentMethod:
        ...

    async def delete_payment_method(
        self,
        payer_id: MixedUuidStrType,
        payment_method_id: str,
        country: CountryCode,
        payer_id_type: str = None,
        payment_method_id_type: str = None,
    ) -> PaymentMethod:
        """
        Implementation of delete/detach a payment method.

        :param payer_id:
        :param payment_method_id:
        :param payer_id_type:
        :param payment_method_id_type:
        :param country:
        :return: PaymentMethod object
        """

        # step 1: get payer by for country information
        raw_payer: Optional[RawPayer] = None
        try:
            raw_payer = await self.payer_client.get_raw_payer(
                payer_id=payer_id, payer_id_type=payer_id_type
            )
        except PayerReadError as e:
            if e.error_code != PayinErrorCode.PAYER_READ_NOT_FOUND:
                raise e
            self.log.info(
                f"[delete_payment_method][{payer_id}][{payer_id_type}] can't find payer. could be DSJ consumer"
            )

        # step 2: find payment_method.
        raw_payment_method: RawPaymentMethod = await self.payment_method_client.get_raw_payment_method(
            payer_id=payer_id,
            payment_method_id=payment_method_id,
            payer_id_type=payer_id_type,
            payment_method_id_type=payment_method_id_type,
        )
        pgp_payment_method_id: str = raw_payment_method.pgp_payment_method_id()

        # step 3: detach PGP payment method
        country_code: CountryCode = CountryCode.US
        if country:
            country_code = country
        else:
            if raw_payer:
                country_code = raw_payer.country()
            else:
                self.log.info(
                    f"[delete_payment_method][{payer_id}][{payer_id_type}] use default country code US"
                )
        await self.payment_method_client.pgp_detach_payment_method(
            payer_id=payer_id,
            pgp_payment_method_id=pgp_payment_method_id,
            country=country_code,
        )

        # step 4: update pgp_payment_method.detached_at
        updated_raw_pm: RawPaymentMethod = await self.payment_method_client.detach_raw_payment_method(
            payer_id=payer_id,
            pgp_payment_method_id=pgp_payment_method_id,
            raw_payment_method=raw_payment_method,
        )

        # step 5: update payer and pgp_customers / stripe_customer to remove the default_payment_method.
        # we don’t need to if it’s DSJ marketplace consumer.
        if raw_payer:
            if raw_payer.pgp_default_payment_method_id() == pgp_payment_method_id:
                self.log.info(
                    f"[delete_payment_method] delete default payment method {pgp_payment_method_id} from pgp_customers table "
                )
                await self.payer_client.update_payer_default_payment_method(
                    raw_payer=raw_payer,
                    pgp_default_payment_method_id=None,
                    payer_id=payer_id,
                    payer_id_type=payer_id_type,
                )
            else:
                self.log.info(
                    f"[delete_payment_method] no need to delete default payment method {raw_payer.pgp_default_payment_method_id}"
                )

        # we dont automatically update the new default payment method for payer

        return updated_raw_pm.to_payment_method()


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
            if (payer_id_type == PayerIdType.DD_PAYMENT_PAYER_ID) or (
                not payer_id_type
            ):
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

            elif payment_method_id_type == PaymentMethodIdType.DD_STRIPE_CARD_SERIAL_ID:
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
                    "[get_payment_method_raw_objects][{payment_method_id}] invalid payment_method_id_type {payment_method_id_type}"
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
                f"[get_payment_method_raw_objects][{payment_method_id}] cant retrieve data from pgp_payment_method and stripe_card tables!"
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
