from abc import abstractmethod
from typing import Optional

from fastapi import Depends
from psycopg2._psycopg import DataError
from structlog import BoundLogger

from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import get_logger_from_req

from app.commons.providers.stripe.stripe_models import (
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
from app.payin.core.payer.model import Payer, RawPayer
from app.payin.core.payer.types import PayerType
from app.payin.core.payment_method.model import RawPaymentMethod
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


class PayerClient:
    """
    Payer client wrapper that provides utilities to Payer.
    """

    def __init__(
        self,
        app_ctxt: AppContext = Depends(get_global_app_context),
        log: BoundLogger = Depends(get_logger_from_req),
        payer_repo: PayerRepository = Depends(PayerRepository.get_repository),
    ):
        self.app_ctxt = app_ctxt
        self.log = log
        self.payer_repo = payer_repo

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
        payer_interface: PayerOpsInterface
        if payer_type == PayerType.MARKETPLACE.value:
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

    async def get_payer_raw_objects(
        self,
        payer_id: str,
        payer_id_type: Optional[str] = None,
        payer_type: Optional[str] = None,
    ) -> RawPayer:
        payer_interface: PayerOpsInterface
        if not payer_id_type or payer_id_type in (
            PayerIdType.DD_PAYMENT_PAYER_ID.value,
            PayerIdType.DD_CONSUMER_ID.value,
        ):
            payer_interface = PayerOps(self.log, self.payer_repo)
        elif payer_id_type in (
            PayerIdType.STRIPE_CUSTOMER_SERIAL_ID.value,
            PayerIdType.STRIPE_CUSTOMER_ID.value,
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

    async def get_payer_raw_object(
        self, payer_id: str, payer_id_type: Optional[str]
    ) -> RawPayer:
        input: GetPayerByIdInput
        if not payer_id_type or payer_id_type == PayerIdType.DD_PAYMENT_PAYER_ID:
            input = GetPayerByIdInput(id=payer_id)
        elif payer_id_type == PayerIdType.DD_CONSUMER_ID:
            input = GetPayerByIdInput(dd_payer_id=payer_id)
        else:
            # TODO: throw exception
            ...

        payer_entity: Optional[PayerDbEntity] = await self.payer_repo.get_payer_by_id(
            request=input
        )
        if not payer_entity:
            raise PayerReadError(
                error_code=PayinErrorCode.PAYER_READ_NOT_FOUND, retryable=False
            )
        return RawPayer(payer_entity=payer_entity)

    async def update_payer_default_payment_method(
        self,
        raw_payer: RawPayer,
        pgp_default_payment_method_id: str,
        payer_id: str,
        payer_type: Optional[str] = None,
        payer_id_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> RawPayer:
        lazy_create: bool = False
        payer_interface: PayerOpsInterface
        if not payer_id_type or payer_id_type in (
            PayerIdType.DD_PAYMENT_PAYER_ID.value,
            PayerIdType.DD_CONSUMER_ID.value,
        ):
            payer_interface = PayerOps(self.log, self.payer_repo)
        elif payer_id_type in (
            PayerIdType.STRIPE_CUSTOMER_SERIAL_ID.value,
            PayerIdType.STRIPE_CUSTOMER_ID.value,
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
            return await self.lazy_create_payer(
                dd_payer_id=str(updated_raw_payer.stripe_customer_entity.owner_id),
                country=updated_raw_payer.stripe_customer_entity.country_shortname,
                pgp_customer_id=updated_raw_payer.stripe_customer_entity.stripe_id,
                pgp_code=PaymentProvider.STRIPE.value,  # hard-code "stripe"
                payer_type=updated_raw_payer.stripe_customer_entity.owner_type,
                default_payment_method_id=pgp_default_payment_method_id,
                description=description,
            )
        return updated_raw_payer

    async def lazy_create_payer(
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

        return await self.create_payer_raw_objects(
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
            stripe_cus_id: CustomerId = await self.app_ctxt.stripe.create_customer(
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

    async def pgp_update_customer_default_payment_method(
        self, country: str, pgp_customer_id: str, default_payment_method_id: str
    ):
        update_cus_req: UpdateCustomer = UpdateCustomer(
            sid=pgp_customer_id,
            invoice_settings=UpdateCustomer.InvoiceSettings(
                default_payment_method=default_payment_method_id
            ),
        )
        try:
            input_country = CountryCode(country)
            stripe_customer = await self.app_ctxt.stripe.update_customer(
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


class PayerProcessor:
    # prevent circular dependency
    from app.payin.core.payment_method.processor import PaymentMethodClient

    def __init__(
        self,
        payment_method_client: PaymentMethodClient = Depends(PaymentMethodClient),
        payer_client: PayerClient = Depends(PayerClient),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.payer_client = payer_client
        self.log = log
        self.payment_method_client = payment_method_client

    async def create(
        self,
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

        :param dd_payer_id: DoorDash client identifier (consumer_id, etc.)
        :param payer_type: Identify the owner type
        :param email: payer email
        :param country: payer country code
        :param description: short description for the payer
        :return: Payer object
        """
        self.log.info(
            f"[create_payer_impl] dd_payer_id:{dd_payer_id}, payer_type:{payer_type}"
        )

        # TODO: we should get pgp_code in different way
        pgp_code = PaymentProvider.STRIPE.value

        # step 1: lookup active payer by dd_payer_id + payer_type, return error if payer already exists
        await self.payer_client.has_existing_payer(
            dd_payer_id=dd_payer_id, payer_type=payer_type
        )

        # step 2: create PGP customer
        pgp_customer_id: CustomerId = await self.payer_client.pgp_create_customer(
            country=country, email=email, description=description
        )

        self.log.info(
            f"[create_payer_impl][{dd_payer_id}] create PGP customer completed. id:[{pgp_customer_id}]"
        )

        # step 3: create Payer/PgpCustomer/StripeCustomer objects
        raw_payer: RawPayer = await self.payer_client.create_payer_raw_objects(
            dd_payer_id=dd_payer_id,
            payer_type=payer_type,
            country=country,
            pgp_customer_id=pgp_customer_id,
            pgp_code=pgp_code,
            description=description,
        )
        return raw_payer.to_payer()

    async def get(
        self,
        payer_id: str,
        payer_id_type: Optional[str],
        payer_type: Optional[str],
        force_update: Optional[bool] = False,
    ):
        """
        Retrieve DoorDash payer

        :param payer_id: payer unique id.
        :param payer_type: Identify the owner type. This is for backward compatibility.
               Caller can ignore it for new consumer who is onboard from
               new payer APIs.
        :param payer_id_type: [string] identify the type of payer_id. Valid values include "dd_payer_id",
               "stripe_customer_id", "stripe_customer_serial_id" (default is "dd_payer_id")
        :return: Payer object
        """
        self.log.info(
            f"[get_payer_impl] payer_id:{payer_id}, payer_id_type:{payer_id_type}"
        )

        # TODO: if force_update is true, we should retrieve the customer from PGP

        raw_payer: RawPayer = await self.payer_client.get_payer_raw_objects(
            payer_id=payer_id, payer_id_type=payer_id_type, payer_type=payer_type
        )
        return raw_payer.to_payer()

    async def update(
        self,
        payer_id: str,
        default_payment_method_id: str,
        country: CountryCode = CountryCode.US,
        payer_id_type: Optional[str] = None,
        payer_type: Optional[str] = None,
        payment_method_id_type: Optional[str] = None,
    ):
        """
        Update DoorDash payer's default payment method.

        :param country:
        :param payer_id: payer unique id.
        :param default_payment_method_id: new default payment_method identity.
        :param payer_id_type: Identify the owner type. This is for backward compatibility.
                              Caller can ignore it for new consumer who is onboard from
                              new payer APIs.
        :param payer_type:
        :param payment_method_id_type:
        :param payer_client: Utility client that manipulates payer objects
        :return: Payer object
        """
        # step 1: find Payer object to get pgp_resource_id. Exception is handled by get_payer_raw_objects()
        raw_payer: RawPayer = await self.payer_client.get_payer_raw_objects(
            payer_id=payer_id, payer_id_type=payer_id_type, payer_type=payer_type
        )

        # step 2: find PaymentMethod object to get pgp_resource_id.
        raw_pm: RawPaymentMethod = await self.payment_method_client.get_payment_method(
            payer_id=payer_id,
            payment_method_id=default_payment_method_id,
            payer_id_type=payer_id_type,
            payment_method_id_type=payment_method_id_type,
        )

        # step 3: call PGP/stripe api to update default payment method
        stripe_customer = await self.payer_client.pgp_update_customer_default_payment_method(
            country=country,
            pgp_customer_id=raw_payer.pgp_customer_id(),
            default_payment_method_id=raw_pm.pgp_payment_method_id(),
        )

        self.log.info(
            f"[update_payer_impl][{payer_id}][{payer_id_type}] PGP update default_payment_method completed:[{stripe_customer.invoice_settings.default_payment_method}]"
        )

        # step 4: update default_payment_method in pgp_customers/stripe_customer table
        updated_raw_payer: RawPayer = await self.payer_client.update_payer_default_payment_method(
            raw_payer=raw_payer,
            pgp_default_payment_method_id=raw_pm.pgp_payment_method_id(),
            payer_id=payer_id,
            payer_type=payer_type,
            payer_id_type=payer_id_type,
        )

        return updated_raw_payer.to_payer()


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
        self, payer_id: str, payer_id_type: Optional[str], payer_type: Optional[str]
    ) -> RawPayer:
        ...

    @abstractmethod
    async def update_payer_default_payment_method(
        self,
        raw_payer: RawPayer,
        pgp_default_payment_method_id: str,
        payer_id: str,
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
            payer_id = generate_object_uuid(ResourceUuidPrefix.PAYER)
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
                id=generate_object_uuid(ResourceUuidPrefix.PGP_CUSTOMER),
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
        self, payer_id: str, payer_id_type: Optional[str], payer_type: Optional[str]
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
                if payer_id_type == PayerIdType.DD_CONSUMER_ID.value
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
        payer_id: str,
        payer_type: Optional[str] = None,
        payer_id_type: Optional[str] = None,
    ) -> RawPayer:
        if raw_payer.pgp_customer_entity:
            # update pgp_customers.default_payment_method_id for marketplace payer
            raw_payer.pgp_customer_entity = await self.payer_repo.update_pgp_customer(
                UpdatePgpCustomerSetInput(
                    default_payment_method_id=pgp_default_payment_method_id
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
            payer_id = generate_object_uuid(ResourceUuidPrefix.PAYER)
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

            stripe_customer_entity = await self.payer_repo.get_stripe_customer(
                GetStripeCustomerInput(stripe_id=pgp_customer_id)
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
                stripe_customer_entity.id,
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
        self, payer_id: str, payer_id_type: Optional[str], payer_type: Optional[str]
    ) -> RawPayer:
        payer_entity: Optional[PayerDbEntity] = None
        pgp_cus_entity: Optional[PgpCustomerDbEntity] = None
        stripe_cus_entity: Optional[StripeCustomerDbEntity] = None
        is_found: bool = False
        try:
            if payer_type and payer_type != PayerType.MARKETPLACE:
                stripe_cus_entity = await self.payer_repo.get_stripe_customer(
                    GetStripeCustomerInput(stripe_id=payer_id)
                    if payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID.value
                    else GetStripeCustomerInput(id=payer_id)
                )
                # payer entity is optional
                payer_entity = await self.payer_repo.get_payer_by_id(
                    request=GetPayerByIdInput(legacy_stripe_customer_id=payer_id)
                )
                is_found = True if stripe_cus_entity else False
            else:
                # TODO: add error handling here
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
        payer_id: str,
        payer_type: Optional[str] = None,
        payer_id_type: Optional[str] = None,
    ) -> RawPayer:
        # update stripe_customer with new default_payment_method
        if raw_payer.stripe_customer_entity:
            raw_payer.stripe_customer_entity = await self.payer_repo.update_stripe_customer(
                UpdateStripeCustomerSetInput(
                    default_card=pgp_default_payment_method_id
                ),
                UpdateStripeCustomerWhereInput(id=raw_payer.stripe_customer_entity.id),
            )
            self.log.info(
                f"[update_payer_impl][{payer_id}][{payer_id_type}] stripe_customer update default_payment_method completed:[{pgp_default_payment_method_id}]"
            )
        return raw_payer
