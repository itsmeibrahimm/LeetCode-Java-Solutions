from abc import abstractmethod
from datetime import datetime
from typing import Optional

from fastapi import Depends
from psycopg2._psycopg import DataError
from stripe.error import StripeError
from structlog.stdlib import BoundLogger

from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import (
    get_logger_from_req,
    get_stripe_async_client_from_req,
)
from app.commons import tracing
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import (
    CreateCustomer,
    CustomerId,
    UpdateCustomer,
    InvoiceSettings,
    Customer as StripeCustomer,
    RetrieveCustomer,
)
from app.commons.types import CountryCode
from app.commons.utils.types import PaymentProvider
from app.commons.utils.uuid import generate_object_uuid
from app.payin.core.exceptions import (
    PayerReadError,
    PayerCreationError,
    PayinErrorCode,
    PayerUpdateError,
)
from app.payin.core.payer.model import RawPayer
from app.payin.core.payer.types import PayerType
from app.payin.core.types import PayerIdType, MixedUuidStrType
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
)


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
                    f"[has_existing_payer][{exist_payer.id}] payer already exists. dd_payer_id:[{dd_payer_id}], payer_type:[{payer_type}]"
                )
                # raise PayerCreationError(
                #     error_code=PayinErrorCode.PAYER_CREATE_PAYER_ALREADY_EXIST,
                #     retryable=False,
                # )
        except DataError as e:
            self.log.error(
                f"[has_existing_payer][{dd_payer_id}] DataError when reading from payers table: {e}"
            )
            raise PayerCreationError(
                error_code=PayinErrorCode.PAYER_READ_DB_ERROR, retryable=True
            )

    async def create_raw_payer(
        self,
        dd_payer_id: str,
        payer_type: str,
        country: str,
        pgp_customer_id: str,
        pgp_code: str,
        description: Optional[str],
        default_payment_method_id: Optional[str] = None,
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
            pgp_customer_id=pgp_customer_id,
            pgp_code=pgp_code,
            description=description,
            default_payment_method_id=default_payment_method_id,
        )

    async def get_raw_payer(
        self,
        payer_id: MixedUuidStrType,
        payer_id_type: Optional[str] = None,
        payer_type: Optional[str] = None,
    ) -> RawPayer:
        payer_interface: PayerOpsInterface
        if not payer_id_type or payer_id_type in (
            PayerIdType.PAYER_ID,
            PayerIdType.DD_CONSUMER_ID,
        ):
            payer_interface = PayerOps(self.log, self.payer_repo)
        elif payer_id_type in (
            PayerIdType.DD_STRIPE_CUSTOMER_SERIAL_ID,
            PayerIdType.STRIPE_CUSTOMER_ID,
        ):
            payer_interface = LegacyPayerOps(self.log, self.payer_repo)
        else:
            self.log.error(
                f"[get_payer_raw_objects][{payer_id}] invalid payer_id_type:[{payer_id_type}]"
            )
            raise PayerReadError(
                error_code=PayinErrorCode.PAYER_READ_INVALID_DATA, retryable=False
            )
        return await payer_interface.get_payer_raw_objects(
            payer_id=payer_id, payer_id_type=payer_id_type, payer_type=payer_type
        )

    async def force_update_payer(
        self, raw_payer: RawPayer, country: Optional[CountryCode] = CountryCode.US
    ) -> RawPayer:
        pgp_customer_id: Optional[
            str
        ] = raw_payer.pgp_customer_id() if raw_payer.pgp_customer_id() else None
        if not pgp_customer_id:
            self.log.info(
                "[force_update_payer] pgp_customer_id is none, skip force update"
            )
            return raw_payer

        # Step 1: retrieve customer from payment provider
        input_country = raw_payer.country() if raw_payer.country() else country
        pgp_customer: StripeCustomer = await self.pgp_get_customer(
            pgp_customer_id=pgp_customer_id, country=CountryCode(input_country)
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
        except DataError as e:
            self.log.error(
                f"[force_update_payer] DataError when reading data from db: {e}"
            )
            raise PayerUpdateError(
                error_code=PayinErrorCode.PAYER_UPDATE_DB_ERROR, retryable=True
            )
        return raw_payer

    async def update_payer_default_payment_method(
        self,
        raw_payer: RawPayer,
        pgp_default_payment_method_id: str,
        payer_id: MixedUuidStrType,
        payer_type: Optional[str] = None,
        payer_id_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> RawPayer:
        lazy_create: bool = False
        payer_interface: PayerOpsInterface
        if not payer_id_type or payer_id_type in (
            PayerIdType.PAYER_ID,
            PayerIdType.DD_CONSUMER_ID,
        ):
            payer_interface = PayerOps(self.log, self.payer_repo)
        elif payer_id_type in (
            PayerIdType.DD_STRIPE_CUSTOMER_SERIAL_ID,
            PayerIdType.STRIPE_CUSTOMER_ID,
        ):
            payer_interface = LegacyPayerOps(self.log, self.payer_repo)
            lazy_create = True
        else:
            self.log.error(
                f"[update_payer_default_payment_method][{payer_id}] invalid payer_id_type:[{payer_id_type}]"
            )
            raise PayerReadError(
                error_code=PayinErrorCode.PAYER_READ_INVALID_DATA, retryable=False
            )
        updated_raw_payer = await payer_interface.update_payer_default_payment_method(
            raw_payer=raw_payer,
            pgp_default_payment_method_id=pgp_default_payment_method_id,
            payer_id=payer_id,
            payer_type=payer_type,
            payer_id_type=payer_id_type,
        )

        if lazy_create is True and updated_raw_payer.stripe_customer_entity:
            return await self.lazy_create_raw_payer(
                dd_payer_id=str(updated_raw_payer.stripe_customer_entity.owner_id),
                country=updated_raw_payer.stripe_customer_entity.country_shortname,
                pgp_customer_id=updated_raw_payer.stripe_customer_entity.stripe_id,
                pgp_code=PaymentProvider.STRIPE,  # hard-code "stripe"
                payer_type=updated_raw_payer.stripe_customer_entity.owner_type,
                default_payment_method_id=pgp_default_payment_method_id,
                description=description,
            )
        return updated_raw_payer

    async def lazy_create_raw_payer(
        self,
        dd_payer_id: str,
        country: str,
        pgp_customer_id: str,
        pgp_code: str,
        payer_type: str,
        default_payment_method_id: Optional[str],
        description: Optional[str] = None,
    ) -> RawPayer:
        # ensure Payer doesn't exist
        get_payer_entity: Optional[
            PayerDbEntity
        ] = await self.payer_repo.get_payer_by_id(
            request=GetPayerByIdInput(legacy_stripe_customer_id=pgp_customer_id)
        )
        if get_payer_entity:
            self.log.info(
                "[lazy_create_payer] payer already exist for stripe_customer %s . payer_id:%s",
                pgp_customer_id,
                get_payer_entity.id,
            )
            return RawPayer(payer_entity=get_payer_entity)

        return await self.create_raw_payer(
            dd_payer_id=dd_payer_id,
            payer_type=payer_type,
            country=country,
            pgp_customer_id=pgp_customer_id,
            pgp_code=pgp_code,
            description=description,
            default_payment_method_id=default_payment_method_id,
        )

    async def pgp_create_customer(
        self, country: str, email: str, description: str
    ) -> CustomerId:
        creat_cus_req: CreateCustomer = CreateCustomer(
            email=email, description=description
        )
        try:
            stripe_cus_id: CustomerId = await self.stripe_async_client.create_customer(
                country=CountryCode(country), request=creat_cus_req
            )
        except Exception as e:
            self.log.error(
                f"[pgp_create_customer] error while creating stripe customer. {e}"
            )
            raise PayerCreationError(
                error_code=PayinErrorCode.PAYER_CREATE_STRIPE_ERROR, retryable=False
            )
        return stripe_cus_id

    async def pgp_get_customer(
        self, pgp_customer_id: str, country: CountryCode
    ) -> StripeCustomer:
        get_cus_req: RetrieveCustomer = RetrieveCustomer(id=pgp_customer_id)
        try:
            stripe_customer: StripeCustomer = await self.stripe_async_client.retrieve_customer(
                country=country, request=get_cus_req
            )
        except StripeError as e:
            self.log.error(
                f"[pgp_get_customer] error while creating stripe customer. {e}"
            )
            if e.http_status == 404:
                raise PayerReadError(
                    error_code=PayinErrorCode.PAYER_READ_STRIPE_ERROR_NOT_FOUND,
                    retryable=False,
                )
            raise PayerReadError(
                error_code=PayinErrorCode.PAYER_READ_STRIPE_ERROR, retryable=False
            )
        return stripe_customer

    async def pgp_update_customer_default_payment_method(
        self,
        pgp_customer_id: str,
        default_payment_method_id: str,
        country: Optional[str],
    ):
        update_cus_req: UpdateCustomer = UpdateCustomer(
            sid=pgp_customer_id,
            invoice_settings=InvoiceSettings(
                default_payment_method=default_payment_method_id
            ),
        )
        try:
            input_country = CountryCode(country)
            stripe_customer = await self.stripe_async_client.update_customer(
                country=input_country, request=update_cus_req
            )
        except Exception as e:
            self.log.error(
                f"[pgp_update_customer_default_payment_method][{pgp_customer_id}][{default_payment_method_id}] error while updating stripe customer {e}"
            )
            raise PayerUpdateError(
                error_code=PayinErrorCode.PAYER_UPDATE_STRIPE_ERROR, retryable=False
            )
        return stripe_customer


class PayerOpsInterface:
    def __init__(self, log: BoundLogger, payer_repo: PayerRepository):
        self.log = log
        self.payer_repo = payer_repo

    @abstractmethod
    async def create_payer_raw_objects(
        self,
        dd_payer_id: str,
        payer_type: str,
        country: str,
        pgp_customer_id: str,
        pgp_code: str,
        description: Optional[str],
        default_payment_method_id: Optional[str] = None,
    ) -> RawPayer:
        ...

    @abstractmethod
    async def get_payer_raw_objects(
        self,
        payer_id: MixedUuidStrType,
        payer_id_type: Optional[str],
        payer_type: Optional[str],
    ) -> RawPayer:
        ...

    @abstractmethod
    async def update_payer_default_payment_method(
        self,
        raw_payer: RawPayer,
        pgp_default_payment_method_id: str,
        payer_id: MixedUuidStrType,
        payer_type: Optional[str] = None,
        payer_id_type: Optional[str] = None,
    ) -> RawPayer:
        ...


class PayerOps(PayerOpsInterface):
    async def create_payer_raw_objects(
        self,
        dd_payer_id: str,
        payer_type: str,
        country: str,
        pgp_customer_id: str,
        pgp_code: str,
        description: Optional[str],
        default_payment_method_id: Optional[str] = None,
    ) -> RawPayer:
        try:
            payer_entity: PayerDbEntity
            pgp_customer_entity: PgpCustomerDbEntity
            payer_id = generate_object_uuid()
            payer_input = InsertPayerInput(
                id=payer_id,
                payer_type=payer_type,
                dd_payer_id=dd_payer_id,
                legacy_stripe_customer_id=pgp_customer_id,
                country=country,
                description=description,
            )
            # create Payer and PgpCustomer objects
            pgp_customer_input = InsertPgpCustomerInput(
                id=generate_object_uuid(),
                payer_id=payer_id,
                pgp_code=pgp_code,
                pgp_resource_id=pgp_customer_id,
                default_payment_method_id=default_payment_method_id,
            )
            payer_entity, pgp_customer_entity = await self.payer_repo.insert_payer_and_pgp_customer(
                payer_input=payer_input, pgp_customer_input=pgp_customer_input
            )
            self.log.info(
                "[create_payer_impl][%s] create payer/pgp_customer completed. stripe_customer_id_id:%s",
                payer_entity.id,
                pgp_customer_id,
            )
        except DataError as e:
            self.log.error(
                f"[create_payer_impl][{pgp_code}] DataError when writing into db. {e}"
            )
            raise PayerCreationError(
                error_code=PayinErrorCode.PAYER_CREATE_INVALID_DATA, retryable=True
            )
        return RawPayer(
            payer_entity=payer_entity, pgp_customer_entity=pgp_customer_entity
        )

    async def get_payer_raw_objects(
        self,
        payer_id: MixedUuidStrType,
        payer_id_type: Optional[str],
        payer_type: Optional[str],
    ) -> RawPayer:
        payer_entity: Optional[PayerDbEntity] = None
        pgp_cus_entity: Optional[PgpCustomerDbEntity] = None
        stripe_cus_entity: Optional[StripeCustomerDbEntity] = None
        is_found: bool = False
        try:
            # FIXME: need to query payer object and use payer_type to decide either retrieve from
            # pgp_customers or stripe_customer
            payer_entity, pgp_cus_entity = await self.payer_repo.get_payer_and_pgp_customer_by_id(
                input=GetPayerByIdInput(dd_payer_id=payer_id)
                if payer_id_type == PayerIdType.DD_CONSUMER_ID
                else GetPayerByIdInput(id=payer_id)
            )
            is_found = True if (payer_entity and pgp_cus_entity) else False
        except DataError as e:
            self.log.error(
                f"[get_payer_raw_objects] DataError when reading data from db: {e}"
            )
            raise PayerReadError(
                error_code=PayinErrorCode.PAYER_READ_DB_ERROR, retryable=False
            )
        if not is_found:
            self.log.error(
                "[get_payer_entity][%s] payer not found:[%s]", payer_id, payer_id_type
            )
            raise PayerReadError(
                error_code=PayinErrorCode.PAYER_READ_NOT_FOUND, retryable=False
            )
        return RawPayer(
            payer_entity=payer_entity,
            pgp_customer_entity=pgp_cus_entity,
            stripe_customer_entity=stripe_cus_entity,
        )

    async def update_payer_default_payment_method(
        self,
        raw_payer: RawPayer,
        pgp_default_payment_method_id: str,
        payer_id: MixedUuidStrType,
        payer_type: Optional[str] = None,
        payer_id_type: Optional[str] = None,
    ) -> RawPayer:
        if raw_payer.pgp_customer_entity:
            # update pgp_customers.default_payment_method_id for marketplace payer
            raw_payer.pgp_customer_entity = await self.payer_repo.update_pgp_customer(
                UpdatePgpCustomerSetInput(
                    default_payment_method_id=pgp_default_payment_method_id,
                    updated_at=datetime.utcnow(),
                ),
                UpdatePgpCustomerWhereInput(id=raw_payer.pgp_customer_entity.id),
            )
        elif raw_payer.stripe_customer_entity:
            # update stripe_customer.default_card for non-marketplace payer
            raw_payer.stripe_customer_entity = await self.payer_repo.update_stripe_customer(
                UpdateStripeCustomerSetInput(
                    default_card=pgp_default_payment_method_id
                ),
                UpdateStripeCustomerWhereInput(id=raw_payer.stripe_customer_entity.id),
            )
        else:
            self.log.info(
                f"[update_payer_default_payment_method][{payer_id}][{payer_id_type}] payer object doesn't exist"
            )

        self.log.info(
            f"[update_payer_default_payment_method][{payer_id}][{payer_id_type}] pgp_customers update default_payment_method completed:[{pgp_default_payment_method_id}]"
        )
        return raw_payer


class LegacyPayerOps(PayerOpsInterface):
    async def create_payer_raw_objects(
        self,
        dd_payer_id: str,
        payer_type: str,
        country: str,
        pgp_customer_id: str,
        pgp_code: str,
        description: Optional[str],
        default_payment_method_id: Optional[str] = None,
    ) -> RawPayer:
        try:
            payer_entity: PayerDbEntity
            stripe_customer_entity: Optional[StripeCustomerDbEntity] = None
            payer_id = generate_object_uuid()
            payer_input = InsertPayerInput(
                id=payer_id,
                payer_type=payer_type,
                dd_payer_id=dd_payer_id,
                legacy_stripe_customer_id=pgp_customer_id,
                country=country,
                description=description,
            )
            # create Payer and StripeCustomer objects
            payer_entity = await self.payer_repo.insert_payer(request=payer_input)
            self.log.info(
                "[create_payer_impl][%s] create payer completed. stripe_customer_id_id:%s",
                payer_entity.id,
                pgp_customer_id,
            )

            stripe_customer_entity = await self.payer_repo.get_stripe_customer_by_stripe_id(
                GetStripeCustomerByStripeIdInput(stripe_id=pgp_customer_id)
            )
            if not stripe_customer_entity:
                try:
                    owner_id = int(dd_payer_id)
                except ValueError as e:
                    self.log.error(
                        f"[create_payer_impl][{dd_payer_id}] Value error for non-numeric value. {e}"
                    )
                    raise PayerCreationError(
                        error_code=PayinErrorCode.PAYER_CREATE_INVALID_DATA,
                        retryable=False,
                    )
                stripe_customer_entity = await self.payer_repo.insert_stripe_customer(
                    request=InsertStripeCustomerInput(
                        stripe_id=pgp_customer_id,
                        country_shortname=country,
                        owner_type=payer_type,
                        owner_id=owner_id,
                        default_card=default_payment_method_id,
                    )
                )
            self.log.info(
                "[create_payer_impl][%s] create stripe_customer completed. stripe_customer.id:%s",
                payer_entity.id,
                stripe_customer_entity.id if stripe_customer_entity else None,
            )
        except DataError as e:
            self.log.error(f"[create_payer_impl] DataError when writing into db. {e}")
            raise PayerCreationError(
                error_code=PayinErrorCode.PAYER_CREATE_INVALID_DATA, retryable=True
            )
        return RawPayer(
            payer_entity=payer_entity, stripe_customer_entity=stripe_customer_entity
        )

    async def get_payer_raw_objects(
        self,
        payer_id: MixedUuidStrType,
        payer_id_type: Optional[str],
        payer_type: Optional[str],
    ) -> RawPayer:
        payer_entity: Optional[PayerDbEntity] = None
        pgp_cus_entity: Optional[PgpCustomerDbEntity] = None
        stripe_cus_entity: Optional[StripeCustomerDbEntity] = None
        is_found: bool = False
        try:
            if payer_type and payer_type != PayerType.MARKETPLACE:
                if payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID:
                    stripe_cus_entity = await self.payer_repo.get_stripe_customer_by_stripe_id(
                        GetStripeCustomerByStripeIdInput(stripe_id=payer_id)
                    )
                else:
                    stripe_cus_entity = await self.payer_repo.get_stripe_customer_by_id(
                        GetStripeCustomerByIdInput(id=payer_id)
                    )
                # payer entity is optional
                payer_entity = await self.payer_repo.get_payer_by_id(
                    request=GetPayerByIdInput(legacy_stripe_customer_id=payer_id)
                )
                is_found = bool(stripe_cus_entity)
            else:
                # lookup payers and pgp_customers first. This happens when client creates payer
                # but use stripe_customer_id to lookup payer
                if payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID:
                    payer_entity, pgp_cus_entity = await self.payer_repo.get_payer_and_pgp_customer_by_id(
                        input=GetPayerByIdInput(legacy_stripe_customer_id=payer_id)
                    )
                    is_found = bool(payer_entity and pgp_cus_entity)
                    if not is_found:
                        # TODO: retrieve from stripe
                        ...
                if not is_found:
                    self.log.error(
                        f"[get_payer_raw_objects][{payer_id}] no record in db, should retrieve from stripe. [{payer_id_type}][{payer_type}]"
                    )
        except DataError as e:
            self.log.error(
                f"[get_payer_entity] DataError when reading data from db: {e}"
            )
            raise PayerReadError(
                error_code=PayinErrorCode.PAYER_READ_DB_ERROR, retryable=False
            )
        if not is_found:
            self.log.error(
                "[get_payer_entity][%s] payer not found:[%s]", payer_id, payer_id_type
            )
            raise PayerReadError(
                error_code=PayinErrorCode.PAYER_READ_NOT_FOUND, retryable=False
            )
        return RawPayer(
            payer_entity=payer_entity,
            pgp_customer_entity=pgp_cus_entity,
            stripe_customer_entity=stripe_cus_entity,
        )

    async def update_payer_default_payment_method(
        self,
        raw_payer: RawPayer,
        pgp_default_payment_method_id: str,
        payer_id: MixedUuidStrType,
        payer_type: Optional[str] = None,
        payer_id_type: Optional[str] = None,
    ) -> RawPayer:
        # update stripe_customer with new default_payment_method
        if raw_payer.stripe_customer_entity:
            raw_payer.stripe_customer_entity = await self.payer_repo.update_stripe_customer(
                UpdateStripeCustomerSetInput(
                    default_source=pgp_default_payment_method_id
                ),
                UpdateStripeCustomerWhereInput(id=raw_payer.stripe_customer_entity.id),
            )
            self.log.info(
                f"[update_payer_impl][{payer_id}][{payer_id_type}] stripe_customer update default_payment_method completed:[{pgp_default_payment_method_id}]"
            )
        return raw_payer