from abc import abstractmethod
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends
from stripe.error import StripeError
from structlog.stdlib import BoundLogger

from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import (
    get_logger_from_req,
    get_stripe_async_client_from_req,
)
from app.commons import tracing
from app.commons.core.errors import DBDataError
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import (
    StripeCreateCustomerRequest,
    CustomerId,
    StripeUpdateCustomerRequest,
    InvoiceSettings,
    Customer as StripeCustomer,
    StripeRetrieveCustomerRequest,
    Customer,
)
from app.commons.runtime import runtime
from app.commons.types import CountryCode, PgpCode
from app.commons.utils.uuid import generate_object_uuid
from app.payin.core.exceptions import (
    PayerReadError,
    PayerCreationError,
    PayinErrorCode,
    PayerUpdateError,
)
from app.payin.core.payer.model import RawPayer
from app.payin.core.payer.types import PayerType
from app.payin.core.payment_method.model import PaymentMethodIds, RawPaymentMethod
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.core.types import (
    PayerIdType,
    MixedUuidStrType,
    PaymentMethodIdType,
    PgpPayerResourceId,
)
from app.payin.repository.payer_repo import (
    InsertPayerInput,
    InsertPgpCustomerInput,
    InsertStripeCustomerInput,
    GetPayerByIdInput,
    UpdatePgpCustomerSetInput,
    UpdateStripeCustomerSetInput,
    UpdateStripeCustomerWhereInput,
    UpdatePgpCustomerWhereInput,
    PayerRepository,
    PayerDbEntity,
    PgpCustomerDbEntity,
    StripeCustomerDbEntity,
    GetPayerByDDPayerIdAndTypeInput,
    GetStripeCustomerByStripeIdInput,
    GetStripeCustomerByIdInput,
    GetPgpCustomerInput,
    GetPayerByLegacyStripeCustomerIdInput,
    GetPayerByDDPayerIdInput,
    UpdatePayerSetInput,
    UpdatePayerWhereInput,
    GetStripeCustomerIdByPayerIdInput,
    GetConsumerIdByPayerIdInput,
)
from app.payin.repository.payment_method_repo import PaymentMethodRepository


@tracing.track_breadcrumb(processor_name="payers")
class PayerClient:
    """
    Payer client wrapper that provides utilities to Payer.
    """

    def __init__(
        self,
        app_ctxt: AppContext = Depends(get_global_app_context),
        log: BoundLogger = Depends(get_logger_from_req),
        payer_repo: PayerRepository = Depends(PayerRepository.get_repository),
        stripe_async_client: StripeAsyncClient = Depends(
            get_stripe_async_client_from_req
        ),
    ):
        self.app_ctxt = app_ctxt
        self.log = log
        self.payer_repo = payer_repo
        self.stripe_async_client = stripe_async_client

    async def has_existing_payer(self, dd_payer_id: str, payer_type: str):
        try:
            exist_payer: Optional[
                PayerDbEntity
            ] = await self.payer_repo.get_payer_by_dd_payer_id_and_payer_type(
                GetPayerByDDPayerIdAndTypeInput(
                    dd_payer_id=dd_payer_id, payer_type=payer_type
                )
            )
            if exist_payer:
                self.log.info(
                    "[has_existing_payer] payer already exists",
                    payer_id=dd_payer_id,
                    payer_type=payer_type,
                )
                # raise PayerCreationError(
                #     error_code=PayinErrorCode.PAYER_CREATE_PAYER_ALREADY_EXIST,
                #     retryable=False,
                # )
        except DBDataError:
            self.log.exception(
                "[has_existing_payer] DBDataError when reading from payers table.",
                dd_payer_id=dd_payer_id,
            )
            raise PayerCreationError(error_code=PayinErrorCode.PAYER_READ_DB_ERROR)

    async def create_raw_payer(
        self,
        dd_payer_id: str,
        payer_type: str,
        country: CountryCode,
        pgp_customer_resource_id: str,
        pgp_code: PgpCode,
        description: Optional[str],
        pgp_payment_method_resource_id: Optional[str] = None,
    ) -> RawPayer:
        payer_interface: PayerOpsInterface
        if payer_type == PayerType.MARKETPLACE:
            payer_interface = PayerOps(self.log, self.payer_repo)
        else:
            payer_interface = LegacyPayerOps(self.log, self.payer_repo)

        return await payer_interface.create_payer_raw_objects(
            dd_payer_id=dd_payer_id,
            payer_type=payer_type,
            country=country,
            pgp_customer_resource_id=pgp_customer_resource_id,
            pgp_code=pgp_code,
            description=description,
            pgp_payment_method_resource_id=pgp_payment_method_resource_id,
        )

    async def get_raw_payer(
        self,
        payer_id: MixedUuidStrType,
        payer_id_type: PayerIdType,
        payer_type: Optional[str] = None,
    ) -> RawPayer:
        payer_interface: PayerOpsInterface
        if not self._is_legacy(payer_id_type=payer_id_type):
            payer_interface = PayerOps(self.log, self.payer_repo)
        else:
            payer_interface = LegacyPayerOps(self.log, self.payer_repo)
        return await payer_interface.get_payer_raw_objects(
            payer_id=payer_id, payer_id_type=payer_id_type, payer_type=payer_type
        )

    async def force_update_payer(
        self, raw_payer: RawPayer, country: CountryCode
    ) -> RawPayer:
        # The behavior on stripe when we delete/detach a card:
        # 1) if the card is default_payment_method: stripe will leave
        # pgp_customer.invoice_settings.default_payment_method as empty
        # 2) if th card is default source: stripe will automatically apply the previous successful card
        # as new default source in pgp_customer.default_source

        pgp_customer_resource_id: PgpPayerResourceId = raw_payer.pgp_payer_resource_id

        # Step 1: retrieve customer from payment provider
        input_country = raw_payer.country() if raw_payer.country() else country
        pgp_customer: StripeCustomer = await self.pgp_get_customer(
            pgp_customer_id=pgp_customer_resource_id, country=CountryCode(input_country)
        )

        self.log.info(
            "[force_update_payer] retrieved stripe_customer",
            pgp_customer_resource_id=pgp_customer_resource_id,
            default_source=pgp_customer.default_source,
            default_payment_method=pgp_customer.invoice_settings.default_payment_method,
        )

        # Step 2: compare the elements
        try:
            need_updated: bool = False
            if raw_payer.pgp_customer_entity:
                pc_input: UpdatePgpCustomerSetInput = UpdatePgpCustomerSetInput(
                    updated_at=datetime.utcnow()
                )
                if pgp_customer.currency != raw_payer.pgp_customer_entity.currency:
                    pc_input.currency = pgp_customer.currency
                    need_updated = True
                if (
                    pgp_customer.default_source
                    != raw_payer.pgp_customer_entity.legacy_default_source_id
                ):
                    pc_input.legacy_default_source_id = pgp_customer.default_source
                    need_updated = True
                if (
                    pgp_customer.invoice_settings.default_payment_method
                    != raw_payer.pgp_customer_entity.default_payment_method_id
                ):
                    pc_input.default_payment_method_id = (
                        pgp_customer.invoice_settings.default_payment_method
                    )
                    need_updated = True
                if need_updated:
                    raw_payer.pgp_customer_entity = await self.payer_repo.update_pgp_customer(
                        request_set=pc_input,
                        request_where=UpdatePgpCustomerWhereInput(
                            id=raw_payer.pgp_customer_entity.id
                        ),
                    )
            elif raw_payer.stripe_customer_entity:
                sc_input: UpdateStripeCustomerSetInput = UpdateStripeCustomerSetInput()
                # default_payment_method_id has higher priority than default_source
                if (
                    pgp_customer.default_source
                    != raw_payer.stripe_customer_entity.default_source
                ):
                    sc_input.default_source = pgp_customer.default_source
                    need_updated = True
                if (
                    pgp_customer.invoice_settings.default_payment_method
                    and pgp_customer.invoice_settings.default_payment_method
                    != raw_payer.stripe_customer_entity.default_source
                ):
                    sc_input.default_source = (
                        pgp_customer.invoice_settings.default_payment_method
                    )
                    need_updated = True
                if need_updated:
                    raw_payer.stripe_customer_entity = await self.payer_repo.update_stripe_customer(
                        request_set=sc_input,
                        request_where=UpdateStripeCustomerWhereInput(
                            id=raw_payer.stripe_customer_entity.id
                        ),
                    )

            # update default_payment_method in payers table.
            if raw_payer.payer_entity:
                need_updated = False
                pgp_default_pm_resource_id: str = (
                    pgp_customer.invoice_settings.default_payment_method
                    or pgp_customer.default_source
                )
                payer_input: UpdatePayerSetInput = UpdatePayerSetInput(
                    updated_at=datetime.now(timezone.utc),
                    legacy_default_dd_stripe_card_id=None,
                )

                if pgp_default_pm_resource_id:
                    payment_method_repo: PaymentMethodRepository = PaymentMethodRepository(
                        context=self.app_ctxt
                    )
                    payment_method_client = PaymentMethodClient(
                        payment_method_repo=payment_method_repo,
                        log=self.log,
                        app_ctxt=self.app_ctxt,
                        stripe_async_client=self.stripe_async_client,
                    )
                    raw_pm: RawPaymentMethod = await payment_method_client.get_raw_payment_method_without_payer_auth(
                        payment_method_id=pgp_default_pm_resource_id,
                        payment_method_id_type=PaymentMethodIdType.STRIPE_PAYMENT_METHOD_ID,
                    )
                    if (
                        raw_payer.payer_entity.default_payment_method_id
                        != raw_pm.payment_method_id
                    ) or (
                        raw_payer.payer_entity.legacy_default_dd_stripe_card_id
                        != raw_pm.legacy_dd_stripe_card_id
                    ):
                        # update default_payment_method_id and default_legacy_dd_stripe_card_id
                        self.log.info(
                            "[force_update_payer] update payer entity",
                            default_payment_method_id=raw_pm.payment_method_id,
                            legacy_default_dd_stripe_card_id=raw_pm.legacy_dd_stripe_card_id,
                        )
                        payer_input.legacy_default_dd_stripe_card_id = (
                            raw_pm.legacy_dd_stripe_card_id
                        )
                        payer_input.default_payment_method_id = raw_pm.payment_method_id
                        need_updated = True
                else:
                    if (
                        raw_payer.payer_entity.default_payment_method_id
                        or raw_payer.payer_entity.legacy_default_dd_stripe_card_id
                    ):
                        self.log.info(
                            "[force_update_payer] update payer entity to cleanup default payment method"
                        )
                        payer_input.legacy_default_dd_stripe_card_id = None
                        payer_input.default_payment_method_id = None
                        need_updated = True
                if need_updated:
                    raw_payer.payer_entity = await self.payer_repo.update_payer_by_id(
                        request_set=payer_input,
                        request_where=UpdatePayerWhereInput(
                            id=raw_payer.payer_entity.id
                        ),
                    )
        except DBDataError:
            self.log.exception(
                "[force_update_payer] DBDataError when reading data from db"
            )
            raise PayerUpdateError(error_code=PayinErrorCode.PAYER_UPDATE_DB_ERROR)
        return raw_payer

    async def update_default_payment_method(
        self,
        raw_payer: RawPayer,
        payment_method_ids: PaymentMethodIds,
        payer_id: MixedUuidStrType,
        payer_id_type: Optional[PayerIdType] = None,
        description: Optional[str] = None,
    ) -> RawPayer:
        lazy_create: bool = False
        payer_interface: PayerOpsInterface
        if not self._is_legacy(payer_id_type=payer_id_type):
            payer_interface = PayerOps(self.log, self.payer_repo)
        else:
            payer_interface = LegacyPayerOps(self.log, self.payer_repo)
            lazy_create = False if raw_payer.payer_entity else True

        updated_raw_payer = await payer_interface.update_payer_default_payment_method(
            raw_payer=raw_payer,
            payment_method_ids=payment_method_ids,
            payer_id=payer_id,
            payer_id_type=payer_id_type,
        )

        runtime_lazy_create: bool = runtime.get_bool(
            "payin/feature-flags/enable_payer_lazy_creation.bool", True
        )

        if runtime_lazy_create and (
            lazy_create and updated_raw_payer.stripe_customer_entity
        ):
            return await self.lazy_create_raw_payer(
                dd_payer_id=str(updated_raw_payer.stripe_customer_entity.owner_id),
                country=CountryCode(
                    updated_raw_payer.stripe_customer_entity.country_shortname
                ),
                pgp_customer_resource_id=updated_raw_payer.stripe_customer_entity.stripe_id,
                pgp_code=PgpCode.STRIPE,
                payer_type=updated_raw_payer.stripe_customer_entity.owner_type,
                pgp_payment_method_res_id=payment_method_ids.pgp_payment_method_resource_id,
                description=description,
            )
        return updated_raw_payer

    async def lazy_create_raw_payer(
        self,
        dd_payer_id: str,
        country: CountryCode,
        pgp_customer_resource_id: str,
        pgp_code: PgpCode,
        payer_type: str,
        pgp_payment_method_res_id: str,
        description: Optional[str] = None,
    ) -> RawPayer:
        # ensure Payer doesn't exist
        get_payer_entity: Optional[
            PayerDbEntity
        ] = await self.payer_repo.get_payer_by_legacy_stripe_customer_id(
            request=GetPayerByLegacyStripeCustomerIdInput(
                legacy_stripe_customer_id=pgp_customer_resource_id
            )
        )
        if get_payer_entity:
            self.log.info(
                "[lazy_create_payer] payer already exist!",
                pgp_customer_res_id=pgp_customer_resource_id,
                payer_id=get_payer_entity.id,
            )
            return RawPayer(payer_entity=get_payer_entity)

        return await self.create_raw_payer(
            dd_payer_id=dd_payer_id,
            payer_type=payer_type,
            country=country,
            pgp_customer_resource_id=pgp_customer_resource_id,
            pgp_code=pgp_code,
            description=description,
            pgp_payment_method_resource_id=pgp_payment_method_res_id,
        )

    async def pgp_create_customer(
        self, country: CountryCode, email: str, description: str
    ) -> CustomerId:
        creat_cus_req: StripeCreateCustomerRequest = StripeCreateCustomerRequest(
            email=email, description=description
        )
        try:
            stripe_cus: Customer = await self.stripe_async_client.create_customer(
                country=country, request=creat_cus_req
            )
        except Exception:
            self.log.exception(
                "[pgp_create_customer] error while creating stripe customer."
            )
            raise PayerCreationError(
                error_code=PayinErrorCode.PAYER_CREATE_STRIPE_ERROR
            )
        return stripe_cus.id

    async def pgp_get_customer(
        self, pgp_customer_id: str, country: CountryCode
    ) -> StripeCustomer:
        get_cus_req: StripeRetrieveCustomerRequest = StripeRetrieveCustomerRequest(
            id=pgp_customer_id
        )
        try:
            stripe_customer: StripeCustomer = await self.stripe_async_client.retrieve_customer(
                country=country, request=get_cus_req
            )
        except StripeError as e:
            self.log.exception(
                "[pgp_get_customer] error while creating stripe customer."
            )
            if e.http_status == 404:
                raise PayerReadError(
                    error_code=PayinErrorCode.PAYER_READ_STRIPE_ERROR_NOT_FOUND
                )
            raise PayerReadError(error_code=PayinErrorCode.PAYER_READ_STRIPE_ERROR)
        return stripe_customer

    async def pgp_update_customer_default_payment_method(
        self,
        pgp_customer_resource_id: str,
        pgp_payment_method_resource_id: str,
        country: str,
    ):
        update_cus_req: StripeUpdateCustomerRequest = StripeUpdateCustomerRequest(
            sid=pgp_customer_resource_id,
            invoice_settings=InvoiceSettings(
                default_payment_method=pgp_payment_method_resource_id
            ),
        )
        try:
            input_country = CountryCode(country)
            stripe_customer = await self.stripe_async_client.update_customer(
                country=input_country, request=update_cus_req
            )
        except Exception as e:
            self.log.exception(
                "[pgp_update_customer_default_payment_method] Error while updating stripe customer",
                pgp_customer_resource_id=pgp_customer_resource_id,
                pgp_payment_method_resource_id=pgp_payment_method_resource_id,
            )
            raise PayerUpdateError(
                error_code=PayinErrorCode.PAYER_UPDATE_STRIPE_ERROR
            ) from e
        return stripe_customer

    async def get_consumer_id_by_payer_id(self, payer_id: str) -> int:
        return await self.payer_repo.get_consumer_id_by_payer_id(
            input=GetConsumerIdByPayerIdInput(payer_id=payer_id)
        )

    def _is_legacy(self, payer_id_type: Optional[PayerIdType] = None):
        if not payer_id_type or payer_id_type in (
            PayerIdType.PAYER_ID,
            PayerIdType.DD_CONSUMER_ID,
        ):
            return False
        return True

    async def get_stripe_customer_id_by_payer_id(self, payer_id: str):
        stripe_customer_id = await self.payer_repo.get_stripe_customer_id_by_payer_id(
            input=GetStripeCustomerIdByPayerIdInput(payer_id=payer_id)
        )
        if not stripe_customer_id:
            self.log.exception(
                "[get_stripe_customer_id_by_payer_id] No stripe_customer_id available for payer: "
            )
            raise PayerReadError(
                error_code=PayinErrorCode.PAYER_READ_STRIPE_ERROR_NOT_FOUND
            )
        return stripe_customer_id


class PayerOpsInterface:
    def __init__(self, log: BoundLogger, payer_repo: PayerRepository):
        self.log = log
        self.payer_repo = payer_repo

    @abstractmethod
    async def create_payer_raw_objects(
        self,
        dd_payer_id: str,
        payer_type: str,
        country: CountryCode,
        pgp_customer_resource_id: str,
        pgp_code: PgpCode,
        description: Optional[str],
        pgp_payment_method_resource_id: Optional[str] = None,
    ) -> RawPayer:
        ...

    @abstractmethod
    async def get_payer_raw_objects(
        self,
        payer_id: MixedUuidStrType,
        payer_id_type: PayerIdType,
        payer_type: Optional[str],
    ) -> RawPayer:
        ...

    async def update_payer_default_payment_method(
        self,
        raw_payer: RawPayer,
        payment_method_ids: PaymentMethodIds,
        payer_id: MixedUuidStrType,
        payer_id_type: Optional[str] = None,
    ) -> RawPayer:
        if raw_payer.payer_entity:
            # update default_payment_method_id and default_legacy_dd_stripe_card_id
            raw_payer.payer_entity = await self.payer_repo.update_payer_by_id(
                request_set=UpdatePayerSetInput(
                    updated_at=datetime.now(timezone.utc),
                    legacy_default_dd_stripe_card_id=payment_method_ids.dd_stripe_card_id,
                    default_payment_method_id=payment_method_ids.payment_method_id,
                ),
                request_where=UpdatePayerWhereInput(id=raw_payer.payer_entity.id),
            )
        if raw_payer.pgp_customer_entity:
            # update pgp_customers.default_payment_method_id for marketplace payer
            raw_payer.pgp_customer_entity = await self.payer_repo.update_pgp_customer(
                UpdatePgpCustomerSetInput(
                    default_payment_method_id=payment_method_ids.pgp_payment_method_resource_id,
                    updated_at=datetime.now(timezone.utc),
                ),
                UpdatePgpCustomerWhereInput(id=raw_payer.pgp_customer_entity.id),
            )
        elif raw_payer.stripe_customer_entity:
            # update stripe_customer.default_card for non-marketplace payer
            raw_payer.stripe_customer_entity = await self.payer_repo.update_stripe_customer(
                UpdateStripeCustomerSetInput(
                    default_source=payment_method_ids.pgp_payment_method_resource_id
                ),
                UpdateStripeCustomerWhereInput(id=raw_payer.stripe_customer_entity.id),
            )
        else:
            self.log.warn(
                "[update_payer_default_payment_method] pgp_customer_entity and stripe_customer_entity dont exist",
                payer_id=payer_id,
                payer_id_type=payer_id_type,
            )

        self.log.info(
            "[update_payer_default_payment_method] pgp_customers update default_payment_method completed",
            payer_id=payer_id,
            payer_id_type=payer_id_type,
            pgp_default_payment_method_id=payment_method_ids.pgp_payment_method_resource_id,
        )
        return raw_payer


class PayerOps(PayerOpsInterface):
    async def create_payer_raw_objects(
        self,
        dd_payer_id: str,
        payer_type: str,
        country: CountryCode,
        pgp_customer_resource_id: str,
        pgp_code: PgpCode,
        description: Optional[str],
        pgp_payment_method_resource_id: Optional[str] = None,
    ) -> RawPayer:
        try:
            payer_entity: PayerDbEntity
            pgp_customer_entity: PgpCustomerDbEntity
            payer_id = generate_object_uuid()
            now = datetime.now(timezone.utc)
            payer_input = InsertPayerInput(
                id=payer_id,
                payer_type=payer_type,
                dd_payer_id=dd_payer_id,
                legacy_stripe_customer_id=pgp_customer_resource_id,
                country=country,
                description=description,
                created_at=now,
                updated_at=now,
            )
            # create Payer and PgpCustomer objects
            now = datetime.now(timezone.utc)
            pgp_customer_input = InsertPgpCustomerInput(
                id=generate_object_uuid(),
                payer_id=payer_id,
                pgp_code=pgp_code,
                pgp_resource_id=pgp_customer_resource_id,
                default_payment_method_id=pgp_payment_method_resource_id,
                country=country,
                is_primary=True,  # is_primary is always True for payer's first pgp_customer
                created_at=now,
                updated_at=now,
            )
            payer_entity, pgp_customer_entity = await self.payer_repo.insert_payer_and_pgp_customer(
                payer_input=payer_input, pgp_customer_input=pgp_customer_input
            )
            self.log.info(
                "[create_payer_impl] create payer/pgp_customer completed.",
                payer_id=payer_entity.id,
                stripe_customer_id=pgp_customer_resource_id,
            )
        except DBDataError:
            self.log.exception(
                "[create_payer_impl] DBDataError when writing into db.",
                pgp_code=pgp_code,
            )
            raise PayerCreationError(
                error_code=PayinErrorCode.PAYER_CREATE_INVALID_DATA
            )
        return RawPayer(
            payer_entity=payer_entity, pgp_customer_entity=pgp_customer_entity
        )

    async def get_payer_raw_objects(
        self,
        payer_id: MixedUuidStrType,
        payer_id_type: PayerIdType,
        payer_type: Optional[str],
    ) -> RawPayer:
        payer_entity: Optional[PayerDbEntity] = None
        pgp_cus_entity: Optional[PgpCustomerDbEntity] = None
        stripe_cus_entity: Optional[StripeCustomerDbEntity] = None
        is_found: bool = False
        try:
            if payer_id_type == PayerIdType.DD_CONSUMER_ID:
                payer_entity = await self.payer_repo.get_payer_by_dd_payer_id(
                    request=GetPayerByDDPayerIdInput(dd_payer_id=payer_id)
                )
            else:
                payer_entity = await self.payer_repo.get_payer_by_id(
                    request=GetPayerByIdInput(id=payer_id)
                )
            if payer_entity:
                if payer_entity.payer_type == PayerType.MARKETPLACE:
                    pgp_cus_entity = await self.payer_repo.get_pgp_customer(
                        request=GetPgpCustomerInput(payer_id=payer_entity.id)
                    )
                    is_found = True if (payer_entity and pgp_cus_entity) else False
                else:
                    stripe_cus_entity = await self.payer_repo.get_stripe_customer_by_stripe_id(
                        request=GetStripeCustomerByStripeIdInput(
                            stripe_id=payer_entity.legacy_stripe_customer_id
                        )
                    )
                    is_found = True if (payer_entity and stripe_cus_entity) else False
        except DBDataError:
            self.log.exception(
                "[get_payer_raw_objects] DBDataError when reading data from db."
            )
            raise PayerReadError(error_code=PayinErrorCode.PAYER_READ_DB_ERROR)
        if not is_found:
            self.log.error(
                "[get_payer_raw_objects] payer not found.",
                payer_id=payer_id,
                payer_id_type=payer_id_type,
            )
            raise PayerReadError(error_code=PayinErrorCode.PAYER_READ_NOT_FOUND)
        return RawPayer(
            payer_entity=payer_entity,
            pgp_customer_entity=pgp_cus_entity,
            stripe_customer_entity=stripe_cus_entity,
        )


class LegacyPayerOps(PayerOpsInterface):
    async def create_payer_raw_objects(
        self,
        dd_payer_id: str,
        payer_type: str,
        country: CountryCode,
        pgp_customer_resource_id: str,
        pgp_code: str,
        description: Optional[str],
        pgp_payment_method_resource_id: Optional[str] = None,
    ) -> RawPayer:
        try:
            now = datetime.now(timezone.utc)
            payer_entity: PayerDbEntity
            stripe_customer_entity: Optional[StripeCustomerDbEntity] = None
            payer_id = generate_object_uuid()
            payer_input = InsertPayerInput(
                id=payer_id,
                payer_type=payer_type,
                dd_payer_id=dd_payer_id,
                legacy_stripe_customer_id=pgp_customer_resource_id,
                country=country,
                description=description,
                created_at=now,
                updated_at=now,
            )
            # create Payer and StripeCustomer objects
            payer_entity = await self.payer_repo.insert_payer(request=payer_input)
            self.log.info(
                "[create_payer_raw_objects] create payer completed.",
                payer_id=payer_entity.id,
                pgp_customer_res_id=pgp_customer_resource_id,
            )

            stripe_customer_entity = await self.payer_repo.get_stripe_customer_by_stripe_id(
                GetStripeCustomerByStripeIdInput(stripe_id=pgp_customer_resource_id)
            )
            if not stripe_customer_entity:
                try:
                    owner_id = int(dd_payer_id)
                except ValueError:
                    self.log.exception(
                        "[create_payer_impl] Value error for non-numeric value.",
                        dd_payer_id=dd_payer_id,
                    )
                    raise PayerCreationError(
                        error_code=PayinErrorCode.PAYER_CREATE_INVALID_DATA
                    )
                stripe_customer_entity = await self.payer_repo.insert_stripe_customer(
                    request=InsertStripeCustomerInput(
                        stripe_id=pgp_customer_resource_id,
                        country_shortname=country,
                        owner_type=payer_type,
                        owner_id=owner_id,
                        default_card=pgp_payment_method_resource_id,
                    )
                )
            self.log.info(
                "[create_payer_raw_objects] create stripe_customer completed.",
                payer_id=payer_entity.id,
            )
        except DBDataError:
            self.log.exception("[create_payer_impl] DBDataError when writing into db.")
            raise PayerCreationError(
                error_code=PayinErrorCode.PAYER_CREATE_INVALID_DATA
            )
        return RawPayer(
            payer_entity=payer_entity, stripe_customer_entity=stripe_customer_entity
        )

    async def get_payer_raw_objects(
        self,
        payer_id: MixedUuidStrType,
        payer_id_type: PayerIdType,
        payer_type: Optional[str],
    ) -> RawPayer:
        payer_entity: Optional[PayerDbEntity] = None
        pgp_cus_entity: Optional[PgpCustomerDbEntity] = None
        stripe_cus_entity: Optional[StripeCustomerDbEntity] = None
        is_found: bool = False
        try:
            if not payer_type or payer_type != PayerType.MARKETPLACE:
                if payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID:
                    stripe_cus_entity = await self.payer_repo.get_stripe_customer_by_stripe_id(
                        GetStripeCustomerByStripeIdInput(stripe_id=payer_id)
                    )
                else:
                    stripe_cus_entity = await self.payer_repo.get_stripe_customer_by_id(
                        GetStripeCustomerByIdInput(id=payer_id)
                    )
                # payer entity is optional
                if stripe_cus_entity:
                    payer_entity = await self.payer_repo.get_payer_by_legacy_stripe_customer_id(
                        request=GetPayerByLegacyStripeCustomerIdInput(
                            legacy_stripe_customer_id=stripe_cus_entity.stripe_id
                        )
                    )
                is_found = bool(stripe_cus_entity)
            else:
                # lookup payers and pgp_customers first. This happens when client creates payer
                # but use stripe_customer_id to lookup payer
                if payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID:
                    payer_entity, pgp_cus_entity = await self.payer_repo.get_payer_and_pgp_customer_by_legacy_stripe_cus_id(
                        input=GetPayerByLegacyStripeCustomerIdInput(
                            legacy_stripe_customer_id=payer_id
                        )
                    )
                    is_found = bool(payer_entity and pgp_cus_entity)
                    if not is_found:
                        # TODO: retrieve from stripe
                        ...
                if not is_found:
                    self.log.error(
                        "[get_payer_raw_objects] no record in db, should retrieve from stripe.",
                        payer_id=payer_id,
                        payer_id_type=payer_id_type,
                    )
        except DBDataError:
            self.log.exception(
                "[get_payer_raw_objects] DBDataError when reading data from db."
            )
            raise PayerReadError(error_code=PayinErrorCode.PAYER_READ_DB_ERROR)
        if not is_found:
            self.log.error(
                "[get_payer_raw_objects] payer not found.",
                payer_id=payer_id,
                payer_id_type=payer_id_type,
            )
            raise PayerReadError(error_code=PayinErrorCode.PAYER_READ_NOT_FOUND)
        return RawPayer(
            payer_entity=payer_entity,
            pgp_customer_entity=pgp_cus_entity,
            stripe_customer_entity=stripe_cus_entity,
        )
