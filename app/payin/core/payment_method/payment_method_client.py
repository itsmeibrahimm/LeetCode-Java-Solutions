from abc import abstractmethod
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import Depends
from structlog.stdlib import BoundLogger

from app.commons import tracing
from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import (
    get_logger_from_req,
    get_stripe_async_client_from_req,
)
from app.commons.core.errors import DBDataError
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import (
    PaymentMethod as StripePaymentMethod,
    StripeAttachPaymentMethodRequest,
    StripeCreatePaymentMethodRequest,
    StripeDetachPaymentMethodRequest,
)
from app.commons.types import CountryCode, PgpCode
from app.commons.utils.uuid import generate_object_uuid
from app.payin.core.exceptions import (
    PayinErrorCode,
    PaymentMethodCreateError,
    PaymentMethodDeleteError,
    PaymentMethodReadError,
)
from app.payin.core.payment_method.model import RawPaymentMethod, PaymentMethod
from app.payin.core.payment_method.types import PaymentMethodSortKey
from app.payin.core.types import (
    MixedUuidStrType,
    PayerIdType,
    PaymentMethodIdType,
    PayerReferenceIdType,
)
from app.payin.repository.payment_method_repo import (
    DeletePgpPaymentMethodByIdSetInput,
    DeletePgpPaymentMethodByIdWhereInput,
    DeleteStripeCardByIdSetInput,
    DeleteStripeCardByIdWhereInput,
    GetDuplicateStripeCardInput,
    GetPgpPaymentMethodByPgpResourceIdInput,
    GetStripeCardByIdInput,
    GetStripeCardByStripeIdInput,
    GetStripeCardsByConsumerIdInput,
    GetStripeCardsByStripeCustomerIdInput,
    InsertPgpPaymentMethodInput,
    InsertStripeCardInput,
    PaymentMethodRepository,
    PgpPaymentMethodDbEntity,
    StripeCardDbEntity,
    InsertPaymentMethodInput,
    GetPgpPaymentMethodByPaymentMethodId,
    ListStripeCardDbEntitiesByStripeCustomerId,
    ListPgpPaymentMethodByStripeCardId,
    ListStripeCardDbEntitiesByConsumerId,
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
        payment_method_id: UUID,
        pgp_code: PgpCode,
        stripe_payment_method: StripePaymentMethod,
        is_scanned: bool,
        is_active: bool,
        payer_id: Optional[UUID] = None,
        dd_consumer_id: Optional[str] = None,
        dd_stripe_customer_id: Optional[str] = None,
    ) -> RawPaymentMethod:
        now = datetime.utcnow()
        try:
            dynamic_last4: Optional[str] = None
            tokenization_method: Optional[str] = None
            if stripe_payment_method.card.wallet:
                dynamic_last4 = stripe_payment_method.card.wallet.dynamic_last4
                tokenization_method = stripe_payment_method.card.wallet.type

            payment_method = await self.payment_method_repo.insert_payment_method(
                pm_input=InsertPaymentMethodInput(
                    id=generate_object_uuid(),
                    payer_id=payer_id,
                    created_at=now,
                    updated_at=now,
                )
            )

            pm_entity = await self.payment_method_repo.insert_pgp_payment_method(
                pm_input=InsertPgpPaymentMethodInput(
                    id=payment_method_id,
                    payer_id=(payer_id if payer_id else None),
                    pgp_code=pgp_code,
                    pgp_resource_id=stripe_payment_method.id,
                    legacy_consumer_id=dd_consumer_id,
                    type=stripe_payment_method.type,
                    object=stripe_payment_method.object,
                    created_at=now,
                    updated_at=now,
                    attached_at=now,
                    payment_method_id=payment_method.id,
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
                    active=is_active,
                    consumer_id=(int(dd_consumer_id) if dd_consumer_id else None),
                    stripe_customer_id=(
                        int(dd_stripe_customer_id) if dd_stripe_customer_id else None
                    ),
                    zip_code=stripe_payment_method.billing_details.address.postal_code,
                    address_line1_check=stripe_payment_method.card.checks.address_line1_check,
                    address_zip_check=stripe_payment_method.card.checks.address_postal_code_check,
                    created_at=now,
                    is_scanned=is_scanned,
                    funding_type=stripe_payment_method.card.funding,
                )
            )

            # TODO: add new state in pgp_payment_methods table to keep track of cross DB consistency

        except DBDataError:
            self.log.exception(
                "[create_raw_payment_method] DBDataError when write db.",
                payer_id=payer_id,
            )
            raise PaymentMethodCreateError(
                error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_DB_ERROR
            )
        return RawPaymentMethod(
            pgp_payment_method_entity=pm_entity, stripe_card_entity=sc_entity
        )

    async def _get_raw_payment_method(
        self,
        payment_method_id: MixedUuidStrType,
        payer_id: Optional[MixedUuidStrType] = None,
        payer_id_type: Optional[str] = None,
        payment_method_id_type: Optional[PaymentMethodIdType] = None,
    ) -> RawPaymentMethod:
        """
        Utility function to get payment_method.

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
                "[_get_payment_method] invalid payment_method_id_type",
                payment_method_id=payment_method_id,
                payment_method_id_type=payment_method_id_type,
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE
            )

        raw_payment_method: RawPaymentMethod = await pm_interface.get_payment_method_raw_objects(
            payer_id=payer_id,
            payment_method_id=payment_method_id,
            payer_id_type=payer_id_type,
            payment_method_id_type=payment_method_id_type,
        )

        self.log.info(
            "[_get_payment_method] find payment_method!!",
            payment_method_id=payment_method_id,
            payer_id=payer_id,
        )
        return raw_payment_method

    async def get_raw_payment_method(
        self,
        payer_id: MixedUuidStrType,
        payment_method_id: MixedUuidStrType,
        payer_id_type: Optional[str] = None,
        payment_method_id_type: Optional[PaymentMethodIdType] = None,
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
        payment_method_id_type: Optional[PaymentMethodIdType] = None,
    ) -> RawPaymentMethod:

        return await self._get_raw_payment_method(
            payment_method_id=payment_method_id,
            payment_method_id_type=payment_method_id_type,
        )

    async def get_duplicate_payment_method(
        self,
        stripe_payment_method: StripePaymentMethod,
        payer_reference_id_type: PayerReferenceIdType,
        pgp_customer_resource_id: str,
        dd_consumer_id: Optional[str] = None,
        dd_stripe_customer_id: Optional[str] = None,
    ) -> RawPaymentMethod:
        try:
            dynamic_last4: Optional[str] = None
            if stripe_payment_method.card.wallet:
                dynamic_last4 = stripe_payment_method.card.wallet.dynamic_last4

            # get stripe_card object
            sc_entity = await self.payment_method_repo.get_duplicate_stripe_card(
                payer_reference_id_type=payer_reference_id_type,
                input=GetDuplicateStripeCardInput(
                    fingerprint=stripe_payment_method.card.fingerprint,
                    dynamic_last4=dynamic_last4 or "",
                    exp_year=str(stripe_payment_method.card.exp_year).zfill(4),
                    exp_month=str(stripe_payment_method.card.exp_month).zfill(2),
                    # external_stripe_customer_id=pgp_customer_resource_id,
                    consumer_id=(int(dd_consumer_id) if dd_consumer_id else None),
                    stripe_customer_id=(
                        int(dd_stripe_customer_id) if dd_stripe_customer_id else None
                    ),
                    active=True,
                ),
            )
            if not sc_entity:
                raise PaymentMethodReadError(
                    error_code=PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND
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
        except DBDataError as e:
            self.log.exception(
                "[get_duplicate_payment_method] DBDataError when read db.",
                stripe_payment_method_id=stripe_payment_method.id,
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_DB_ERROR
            ) from e

    async def detach_raw_payment_method(
        self, pgp_payment_method_id: str, raw_payment_method: RawPaymentMethod
    ) -> RawPaymentMethod:
        updated_pm_entity: Optional[PgpPaymentMethodDbEntity] = None
        updated_sc_entity: StripeCardDbEntity
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
        except DBDataError as e:
            self.log.exception(
                "[detach_payment_method] DBDataError when read db.",
                pgp_payment_method_id=pgp_payment_method_id,
            )
            raise PaymentMethodDeleteError(
                error_code=PayinErrorCode.PAYMENT_METHOD_DELETE_DB_ERROR
            ) from e
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
                    type="card",
                    card=StripeCreatePaymentMethodRequest.TokenizedCard(token=token),
                ),
            )

            self.log.info(
                "[pgp_create_and_attach_payment_method] create payment_method completed.",
                pgp_payment_method_res_id=stripe_payment_method.id,
            )
        except Exception as e:
            self.log.exception(
                "[create_payment_method_impl] error while creating stripe payment method."
            )
            raise PaymentMethodCreateError(
                error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_STRIPE_ERROR
            ) from e
        return stripe_payment_method

    async def pgp_attach_payment_method(
        self, pgp_payment_method_res_id: str, pgp_customer_id: str, country: CountryCode
    ) -> StripePaymentMethod:
        try:
            attach_payment_method = await self.stripe_async_client.attach_payment_method(
                country=country,
                request=StripeAttachPaymentMethodRequest(
                    payment_method=pgp_payment_method_res_id, customer=pgp_customer_id
                ),
            )
            self.log.info(
                "[pgp_create_and_attach_payment_method] attach payment_method completed.",
                pgp_customer_id=pgp_customer_id,
                response_customer_id=attach_payment_method.customer,
            )
        except Exception as e:
            self.log.exception(
                "[create_payment_method_impl] error while creating stripe payment method.",
                pgp_customer_id=pgp_customer_id,
            )
            raise PaymentMethodCreateError(
                error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_STRIPE_ERROR
            ) from e
        return attach_payment_method

    async def pgp_detach_payment_method(
        self, pgp_payment_method_id: str, country: CountryCode
    ) -> StripePaymentMethod:
        try:
            stripe_payment_method = await self.stripe_async_client.detach_payment_method(
                country=country,  # TODO: get from payer
                request=StripeDetachPaymentMethodRequest(
                    payment_method=pgp_payment_method_id
                ),
            )
            self.log.info(
                "[pgp_detach_payment_method] detach payment method completed. customer in stripe response blob:",
                pgp_payment_method_id=pgp_payment_method_id,
            )
        except Exception as e:
            self.log.exception(
                "[pgp_detach_payment_method] error while detaching stripe payment method",
                pgp_payment_method_id=pgp_payment_method_id,
            )
            raise PaymentMethodDeleteError(
                error_code=PayinErrorCode.PAYMENT_METHOD_DELETE_STRIPE_ERROR
            ) from e
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
        except DBDataError as e:
            self.log.exception(
                "[get_dd_stripe_card_ids_by_stripe_customer_id] DBDataError when read db.",
                stripe_customer_id=stripe_customer_id,
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_DB_ERROR
            ) from e
        stripe_card_ids = [entity.id for entity in stripe_customer_db_entities]
        return stripe_card_ids

    async def get_stripe_card_ids_for_consumer_id(self, consumer_id: int):
        stripe_card_db_entities = await self.payment_method_repo.get_stripe_cards_by_consumer_id(
            input=GetStripeCardsByConsumerIdInput(consumer_id=consumer_id)
        )
        return [entity.id for entity in stripe_card_db_entities]

    async def get_payment_method_list_by_dd_consumer_id(
        self,
        dd_consumer_id: str,
        country: CountryCode,
        active_only: bool,
        force_update: bool,
        sort_by: PaymentMethodSortKey,
    ) -> List[PaymentMethod]:
        stripe_card_db_entities: List[
            StripeCardDbEntity
        ] = await self.payment_method_repo.list_stripe_card_db_entities_by_consumer_id(
            input=ListStripeCardDbEntitiesByConsumerId(dd_consumer_id=dd_consumer_id)
        )
        return await self._build_payment_methods_by_stripe_cards(
            stripe_card_db_entities=stripe_card_db_entities,
            country=country,
            active_only=active_only,
            sort_by=sort_by,
        )

    async def get_payment_method_list_by_stripe_customer_id(
        self,
        stripe_customer_id: str,
        country: CountryCode,
        active_only: bool,
        force_update: bool,
        sort_by: PaymentMethodSortKey,
    ) -> List[PaymentMethod]:
        stripe_card_db_entities: List[
            StripeCardDbEntity
        ] = await self.payment_method_repo.list_stripe_card_db_entities_by_stripe_customer_id(
            input=ListStripeCardDbEntitiesByStripeCustomerId(
                stripe_customer_id=stripe_customer_id
            )
        )
        return await self._build_payment_methods_by_stripe_cards(
            stripe_card_db_entities=stripe_card_db_entities,
            country=country,
            active_only=active_only,
            sort_by=sort_by,
        )

    async def _build_payment_methods_by_stripe_cards(
        self,
        stripe_card_db_entities: List[StripeCardDbEntity],
        country: CountryCode,
        active_only: bool,
        sort_by: PaymentMethodSortKey,
    ) -> List[PaymentMethod]:
        stripe_card_ids: List[str] = [
            stripe_card_db_entity.stripe_id
            for stripe_card_db_entity in stripe_card_db_entities
        ]
        pgp_payment_method_db_entities: List[
            PgpPaymentMethodDbEntity
        ] = await self.payment_method_repo.list_pgp_payment_method_entities_by_stripe_card_ids(
            input=ListPgpPaymentMethodByStripeCardId(stripe_id_list=stripe_card_ids)
        )
        payment_method_list: List[PaymentMethod] = self._build_payment_method_list(
            pgp_payment_method_db_entities=pgp_payment_method_db_entities,
            stripe_card_db_entities=stripe_card_db_entities,
            country=country,
            active_only=active_only,
        )
        if sort_by == PaymentMethodSortKey.CREATED_AT:
            payment_method_list = sorted(
                payment_method_list,
                key=lambda payment_method: payment_method.created_at,
            )
        return payment_method_list

    def _build_payment_method_list(
        self,
        pgp_payment_method_db_entities: List[PgpPaymentMethodDbEntity],
        stripe_card_db_entities: List[StripeCardDbEntity],
        country: CountryCode,
        active_only: bool,
    ) -> List[PaymentMethod]:
        payment_method_list: List[PaymentMethod] = []
        for sc_entity in stripe_card_db_entities:
            if (
                sc_entity
                and ((active_only and sc_entity.active) or not active_only)
                and (sc_entity.country_of_origin == country)
            ):
                pgp_payment_method_entity = next(
                    (
                        pgp_payment_method_db_entity
                        for pgp_payment_method_db_entity in pgp_payment_method_db_entities
                        if pgp_payment_method_db_entity.pgp_resource_id
                        == sc_entity.stripe_id
                    ),
                    None,
                )
                payment_method_list.append(
                    RawPaymentMethod(
                        stripe_card_entity=sc_entity,
                        pgp_payment_method_entity=pgp_payment_method_entity,
                    ).to_payment_method()
                )
        return payment_method_list


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
                input=GetPgpPaymentMethodByPaymentMethodId(id=payment_method_id)
            )
            # get stripe_card object
            if pm_entity:
                sc_entity = await self.payment_method_repo.get_stripe_card_by_stripe_id(
                    GetStripeCardByStripeIdInput(stripe_id=pm_entity.pgp_resource_id)
                )
        except DBDataError as e:
            self.log.exception(
                "[get_payment_method_raw_objects] DBDataError when read db",
                payer_id=payer_id,
                payment_method_id=payment_method_id,
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_DB_ERROR
            ) from e

        if not (pm_entity and sc_entity):
            self.log.error(
                "[get_payment_method_raw_objects] cant retrieve data from pgp_payment_method and stripe_card tables!",
                payment_method_id=payment_method_id,
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND
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
                "[get_payment_method_raw_objects] payer doesn't own payment_method.",
                payment_method_id=payment_method_id,
                payer_id=payer_id,
                payer_id_type=payer_id_type,
                payment_method_id_type=payment_method_id_type,
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH
            )

        self.log.info(
            "[get_payment_method_raw_objects] find payment_method!",
            payment_method_id=payment_method_id,
            payer_id=payer_id,
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
                    "[get_payment_method_raw_objects] invalid payment_method_id_type",
                    payment_method_id=payment_method_id,
                    payment_method_id_type=payment_method_id_type,
                )
                raise PaymentMethodReadError(
                    error_code=PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE
                )
        except DBDataError as e:
            self.log.exception(
                "[get_payment_method_raw_objects] DBDataError when read db.",
                payer_id=payer_id,
                payment_method_id=payment_method_id,
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_DB_ERROR
            ) from e

        if not sc_entity:
            self.log.error(
                "[get_payment_method_raw_objects] cant retrieve data from pgp_payment_method and stripe_card tables!",
                payment_method_id=payment_method_id,
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND
            )

        is_owner: bool = False
        if not payer_id:
            # no need to authorize payment_method
            is_owner = True
        else:
            if pm_entity and (
                payer_id_type is None or payer_id_type == PayerIdType.PAYER_ID
            ):
                is_owner = payer_id == pm_entity.payer_id
            elif payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID and sc_entity:
                is_owner = payer_id == sc_entity.external_stripe_customer_id
        if is_owner is False:
            self.log.warn(
                "[get_payment_method_raw_objects] payer doesn't own payment_method. ",
                payment_method_id=payment_method_id,
                payment_method_id_type=payment_method_id_type,
                payer_id=payer_id,
                payer_id_type=payer_id_type,
            )
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH
            )

        self.log.info(
            "[get_payment_method_raw_objects] find payment_method!",
            payment_method_id=payment_method_id,
            payer_id=payer_id,
        )

        return RawPaymentMethod(
            pgp_payment_method_entity=pm_entity, stripe_card_entity=sc_entity
        )
