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
from app.commons.types import CountryCode, PgpCode
from app.commons.utils.uuid import generate_object_uuid
from app.payin.core.exceptions import (
    PayerReadError,
    PayerCreationError,
    PayinErrorCode,
    PayerUpdateError,
)
from app.payin.core.payer.model import RawPayer
from app.payin.core.payment_method.model import PaymentMethodIds, RawPaymentMethod
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.core.types import (
    PayerIdType,
    MixedUuidStrType,
    PaymentMethodIdType,
    PgpPayerResourceId,
    PayerReferenceIdType,
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
    GetStripeCustomerByStripeIdInput,
    GetStripeCustomerByIdInput,
    GetPgpCustomerInput,
    GetPayerByLegacyStripeCustomerIdInput,
    UpdatePayerSetInput,
    UpdatePayerWhereInput,
    GetStripeCustomerIdByPayerIdInput,
    GetConsumerIdByPayerIdInput,
    GetPayerByPayerRefIdAndTypeInput,
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

    async def has_existing_payer(
        self, payer_reference_id: str, payer_reference_id_type: PayerReferenceIdType
    ):
        try:
            exist_payer: Optional[
                PayerDbEntity
            ] = await self.payer_repo.get_payer_by_reference_id_and_type(
                input=GetPayerByPayerRefIdAndTypeInput(
                    payer_reference_id=payer_reference_id,
                    payer_reference_id_type=payer_reference_id_type,
                )
            )
            if exist_payer:
                self.log.error(
                    "[has_existing_payer] payer already exists",
                    payer_reference_id=payer_reference_id,
                    payer_reference_id_type=payer_reference_id_type,
                )
                # raise PayerCreationError(
                #     error_code=PayinErrorCode.PAYER_CREATE_PAYER_ALREADY_EXIST,
                #     retryable=False,
                # )
        except DBDataError:
            self.log.exception(
                "[has_existing_payer] DBDataError when reading from payers table.",
                payer_reference_id=payer_reference_id,
                payer_reference_id_type=payer_reference_id_type,
            )
            raise PayerCreationError(error_code=PayinErrorCode.PAYER_READ_DB_ERROR)

    def _payer_reference_id_type_to_owner_type(
        self, payer_reference_id_type: PayerReferenceIdType
    ) -> str:
        if payer_reference_id_type == PayerReferenceIdType.DD_DRIVE_BUSINESS_ID:
            return "business"
        elif payer_reference_id_type == PayerReferenceIdType.DD_DRIVE_MERCHANT_ID:
            return "merchant"
        elif payer_reference_id_type == PayerReferenceIdType.DD_DRIVE_STORE_ID:
            return "store"
        self.log.exception(
            "[_payer_reference_id_type_to_owner_type] in valid type for drive.",
            payer_reference_id_type=payer_reference_id_type,
        )
        raise PayerCreationError(error_code=PayinErrorCode.PAYER_CREATE_INVALID_DATA)

    async def create_raw_payer(
        self,
        payer_reference_id: str,
        payer_reference_id_type: PayerReferenceIdType,
        country: CountryCode,
        pgp_customer_resource_id: str,
        pgp_code: PgpCode,
        description: Optional[str],
        pgp_payment_method_resource_id: Optional[str] = None,
    ) -> RawPayer:

        is_drive: bool = payer_reference_id_type in (
            PayerReferenceIdType.DD_DRIVE_BUSINESS_ID,
            PayerReferenceIdType.DD_DRIVE_STORE_ID,
            PayerReferenceIdType.DD_DRIVE_MERCHANT_ID,
        )
        stripe_customer_entity: Optional[StripeCustomerDbEntity] = None
        if is_drive:
            # double write StripeCustomer object in maindb.stripe_customer table
            try:
                stripe_customer_entity = await self.payer_repo.get_stripe_customer_by_stripe_id(
                    GetStripeCustomerByStripeIdInput(stripe_id=pgp_customer_resource_id)
                )
                if not stripe_customer_entity:
                    stripe_customer_entity = await self.payer_repo.insert_stripe_customer(
                        request=InsertStripeCustomerInput(
                            stripe_id=pgp_customer_resource_id,
                            country_shortname=country,
                            owner_type=self._payer_reference_id_type_to_owner_type(
                                payer_reference_id_type=payer_reference_id_type
                            ),
                            owner_id=int(payer_reference_id),
                            default_card=pgp_payment_method_resource_id,
                        )
                    )
            except DBDataError:
                self.log.exception(
                    "[create_payer_impl] DBDataError when writing into db."
                )
                raise PayerCreationError(
                    error_code=PayinErrorCode.PAYER_CREATE_INVALID_DATA
                )

        # create Payer and PgpCustomer objects
        payer_entity: PayerDbEntity
        pgp_customer_entity: PgpCustomerDbEntity
        payer_id = generate_object_uuid()
        now = datetime.now(timezone.utc)
        payer_input = InsertPayerInput(
            id=payer_id,
            payer_reference_id=payer_reference_id,
            payer_reference_id_type=payer_reference_id_type,
            legacy_stripe_customer_id=pgp_customer_resource_id,
            country=country,
            description=description,
            created_at=now,
            updated_at=now,
        )
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
        try:
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
            payer_entity=payer_entity,
            pgp_customer_entity=pgp_customer_entity,
            stripe_customer_entity=stripe_customer_entity,
        )

    async def get_raw_payer(
        self,
        mixed_payer_id: MixedUuidStrType,
        payer_reference_id_type: PayerReferenceIdType,
    ) -> RawPayer:

        payer_entity: Optional[PayerDbEntity] = None
        pgp_cus_entity: Optional[PgpCustomerDbEntity] = None
        stripe_cus_entity: Optional[StripeCustomerDbEntity] = None
        is_found: bool = False

        try:
            if payer_reference_id_type == PayerReferenceIdType.PAYER_ID:
                # get payer object
                payer_entity = await self.payer_repo.get_payer_by_id(
                    request=GetPayerByIdInput(id=mixed_payer_id)
                )
                if payer_entity:
                    # get pgp_customer object
                    pgp_cus_entity = await self.payer_repo.get_pgp_customer(
                        request=GetPgpCustomerInput(payer_id=payer_entity.id)
                    )
                    # get stripe_customer object
                    stripe_cus_entity = await self.payer_repo.get_stripe_customer_by_stripe_id(
                        GetStripeCustomerByStripeIdInput(
                            stripe_id=payer_entity.legacy_stripe_customer_id
                        )
                    )
                is_found = bool(payer_entity and pgp_cus_entity)
            elif payer_reference_id_type == PayerReferenceIdType.DD_CONSUMER_ID:
                # get payer object
                payer_entity = await self.payer_repo.get_payer_by_reference_id_and_type(
                    input=GetPayerByPayerRefIdAndTypeInput(
                        payer_reference_id=mixed_payer_id,
                        payer_reference_id_type=payer_reference_id_type,
                    )
                )
                # get pgp_customer object
                if payer_entity:
                    pgp_cus_entity = await self.payer_repo.get_pgp_customer(
                        request=GetPgpCustomerInput(payer_id=payer_entity.id)
                    )
                is_found = bool(payer_entity and pgp_cus_entity)
            elif payer_reference_id_type == PayerReferenceIdType.DD_STRIPE_CUSTOMER_ID:
                # get stripe_customer object
                stripe_cus_entity = await self.payer_repo.get_stripe_customer_by_id(
                    GetStripeCustomerByIdInput(id=mixed_payer_id)
                )
                # get payer/pgp_customer objects
                if stripe_cus_entity:
                    payer_entity, pgp_cus_entity = await self.payer_repo.get_payer_and_pgp_customer_by_legacy_stripe_cus_id(
                        input=GetPayerByLegacyStripeCustomerIdInput(
                            legacy_stripe_customer_id=stripe_cus_entity.stripe_id
                        )
                    )
                is_found = bool(stripe_cus_entity)
            elif payer_reference_id_type == PayerReferenceIdType.STRIPE_CUSTOMER_ID:
                # get payer/pgp_customer objects
                payer_entity, pgp_cus_entity = await self.payer_repo.get_payer_and_pgp_customer_by_legacy_stripe_cus_id(
                    input=GetPayerByLegacyStripeCustomerIdInput(
                        legacy_stripe_customer_id=mixed_payer_id
                    )
                )
                # get stripe_customer object
                stripe_cus_entity = await self.payer_repo.get_stripe_customer_by_stripe_id(
                    GetStripeCustomerByStripeIdInput(stripe_id=mixed_payer_id)
                )
                is_found = bool(payer_entity and pgp_cus_entity)
        except DBDataError:
            self.log.exception(
                "[get_payer_raw_objects] DBDataError when reading data from db."
            )
            raise PayerReadError(error_code=PayinErrorCode.PAYER_READ_DB_ERROR)

        if not is_found:
            self.log.error(
                "[get_payer_raw_objects] payer not found.",
                mixed_payer_id=mixed_payer_id,
                payer_reference_id_type=payer_reference_id_type,
            )
            raise PayerReadError(error_code=PayinErrorCode.PAYER_READ_NOT_FOUND)
        return RawPayer(
            payer_entity=payer_entity,
            pgp_customer_entity=pgp_cus_entity,
            stripe_customer_entity=stripe_cus_entity,
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
            if raw_payer.stripe_customer_entity:
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
        self, raw_payer: RawPayer, payment_method_ids: PaymentMethodIds
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
        if raw_payer.stripe_customer_entity:
            # update stripe_customer.default_card for non-marketplace payer
            raw_payer.stripe_customer_entity = await self.payer_repo.update_stripe_customer(
                UpdateStripeCustomerSetInput(
                    default_source=payment_method_ids.pgp_payment_method_resource_id
                ),
                UpdateStripeCustomerWhereInput(id=raw_payer.stripe_customer_entity.id),
            )

        self.log.info(
            "[update_default_payment_method] pgp_customers update default_payment_method completed",
            pgp_cusotmer_resource_id=raw_payer.pgp_payer_resource_id,
            pgp_default_payment_method_id=payment_method_ids.pgp_payment_method_resource_id,
        )

        return raw_payer

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
