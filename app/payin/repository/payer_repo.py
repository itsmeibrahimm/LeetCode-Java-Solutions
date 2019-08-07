from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from gino import GinoConnection
from typing_extensions import final

from app.commons.database.model import DBRequestModel, DBEntity
from app.payin.models.maindb import stripe_customers
from app.payin.models.paymentdb import payers, pgp_customers
from app.payin.repository.base import PayinDBRepository


###########################################################
# Payer DBEntity and CRUD operations                      #
###########################################################
class PayerDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: str
    payer_type: str
    country: str
    legacy_stripe_customer_id: Optional[str] = None
    account_balance: Optional[int] = None
    description: Optional[str] = None
    dd_payer_id: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class InsertPayerInput(PayerDbEntity):
    pass


class InsertPayerOutput(PayerDbEntity):
    pass


class GetPayerByIdInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    id: Optional[str]
    legacy_stripe_customer_id: Optional[str]


class GetPayerByIdOutput(PayerDbEntity):
    pass


###########################################################
# PgpCustomer DBEntity and CRUD operations                #
###########################################################
class PgpCustomerDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: str
    payer_id: str
    pgp_resource_id: str
    currency: Optional[str] = None
    pgp_code: Optional[str] = None
    legacy_id: Optional[int] = None
    legacy_stripe_customer_id: Optional[str] = None
    account_balance: Optional[int] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class InsertPgpCustomerInput(PgpCustomerDbEntity):
    pass


class InsertPgpCustomerOutput(PgpCustomerDbEntity):
    pass


class GetPgpCustomerInput(DBRequestModel):
    payer_id: str
    pgp_code: Optional[str]


class GetPgpCustomerOutput(PgpCustomerDbEntity):
    pass


class UpdatePgpCustomerSetInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    default_payment_method_id: Optional[str]
    legacy_default_source_id: Optional[str]
    legacy_default_card_id: Optional[str]


class UpdatePgpCustomerWhereInput(DBRequestModel):
    id: str


class UpdatePgpCustomerOutput(PgpCustomerDbEntity):
    pass


###########################################################
# StripeCustomer DBEntity and CRUD operations             #
###########################################################
class StripeCustomerDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: int
    stripe_id: str
    country_shortname: str
    owner_type: str
    owner_id: int
    default_card: Optional[str]
    default_source: Optional[str]


class InsertStripeCustomerInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    stripe_id: str
    country_shortname: str
    owner_type: str
    owner_id: int
    default_card: Optional[str]
    default_source: Optional[str]


class InsertStripeCustomerOutput(StripeCustomerDbEntity):
    pass


class GetStripeCustomerInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    id: Optional[int]
    stripe_id: Optional[str]


class GetStripeCustomerOutput(StripeCustomerDbEntity):
    pass


class UpdateStripeCustomerSetInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    default_card: Optional[str]
    default_source: Optional[str]


class UpdateStripeCustomerWhereInput(DBRequestModel):
    id: int


class UpdateStripeCustomerOutput(StripeCustomerDbEntity):
    pass


class PayerRepositoryInterface:
    """
    Payer repository interface class that exposes complicated CRUD operations APIs for business layer.
    """

    @abstractmethod
    async def insert_payer(self, request: InsertPayerInput) -> InsertPayerOutput:
        ...

    @abstractmethod
    async def get_payer_by_id(
        self, request: GetPayerByIdInput
    ) -> Optional[GetPayerByIdOutput]:
        ...

    @abstractmethod
    async def insert_pgp_customer(
        self, request: InsertPgpCustomerInput
    ) -> InsertPgpCustomerOutput:
        ...

    @abstractmethod
    async def get_pgp_customer(
        self, request: GetPgpCustomerInput
    ) -> GetPgpCustomerOutput:
        ...

    @abstractmethod
    async def update_pgp_customer(
        self,
        request_set: UpdatePgpCustomerSetInput,
        request_where: UpdatePgpCustomerWhereInput,
    ) -> UpdatePgpCustomerOutput:
        ...

    @abstractmethod
    async def insert_stripe_customer(
        self, request: InsertStripeCustomerInput
    ) -> InsertStripeCustomerOutput:
        ...

    @abstractmethod
    async def get_stripe_customer(
        self, request: GetStripeCustomerInput
    ) -> GetStripeCustomerOutput:
        ...

    @abstractmethod
    async def update_stripe_customer(
        self,
        request_set: UpdateStripeCustomerSetInput,
        request_where: UpdateStripeCustomerWhereInput,
    ) -> UpdateStripeCustomerOutput:
        ...


@final
@dataclass
class PayerRepository(PayerRepositoryInterface, PayinDBRepository):
    """
    Payer repository class that exposes complicated CRUD operations APIs for business layer.
    """

    async def insert_payer(self, request: InsertPayerInput) -> InsertPayerOutput:
        async with self.payment_database.master().acquire() as conn:  # type: GinoConnection
            stmt = (
                payers.table.insert()
                .values(request.dict(skip_defaults=True))
                .returning(*payers.table.columns.values())
            )
            row = await conn.execution_options(
                timeout=self.payment_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return InsertPayerOutput.from_orm(row)

    async def get_payer_by_id(
        self, request: GetPayerByIdInput
    ) -> Optional[GetPayerByIdOutput]:
        async with self.payment_database.master().acquire() as conn:  # type: GinoConnection
            if request.id:
                stmt = payers.table.select().where(payers.id == request.id)
            else:
                # the "id" below is for the damn silly pre-commit-mypy formatter error
                id = request.legacy_stripe_customer_id
                stmt = payers.table.select().where(
                    payers.legacy_stripe_customer_id == id
                )
            row = await conn.execution_options(
                timeout=self.payment_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return GetPayerByIdOutput.from_orm(row) if row else None

    async def insert_pgp_customer(
        self, request: InsertPgpCustomerInput
    ) -> InsertPgpCustomerOutput:
        async with self.payment_database.master().acquire() as conn:  # type: GinoConnection
            stmt = (
                pgp_customers.table.insert()
                .values(request.dict(skip_defaults=True))
                .returning(*pgp_customers.table.columns.values())
            )
            row = await conn.execution_options(
                timeout=self.payment_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return InsertPgpCustomerOutput.from_orm(row)

    async def get_pgp_customer(
        self, request: GetPgpCustomerInput
    ) -> GetPgpCustomerOutput:
        async with self.payment_database.master().acquire() as conn:  # type: GinoConnection
            stmt = pgp_customers.table.select().where(
                pgp_customers.payer_id == request.payer_id
            )
            row = await conn.execution_options(
                timeout=self.payment_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return GetPgpCustomerOutput.from_orm(row)

    async def update_pgp_customer(
        self,
        request_set: UpdatePgpCustomerSetInput,
        request_where: UpdatePgpCustomerWhereInput,
    ) -> UpdatePgpCustomerOutput:
        async with self.payment_database.master().acquire() as conn:  # type: GinoConnection
            stmt = (
                pgp_customers.table.update()
                .where(pgp_customers.id == request_where.id)
                .values(request_set.dict(skip_defaults=True))
                .returning(*pgp_customers.table.columns.values())
            )
            row = await conn.execution_options(
                timeout=self.payment_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return UpdatePgpCustomerOutput.from_orm(row)

    async def insert_stripe_customer(
        self, request: InsertStripeCustomerInput
    ) -> InsertStripeCustomerOutput:
        async with self.main_database.master().acquire() as conn:  # type: GinoConnection
            stmt = (
                stripe_customers.table.insert()
                .values(request.dict(skip_defaults=True))
                .returning(*stripe_customers.table.columns.values())
            )
            row = await conn.execution_options(
                timeout=self.main_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return InsertStripeCustomerOutput.from_orm(row)

    async def get_stripe_customer(
        self, request: GetStripeCustomerInput
    ) -> GetStripeCustomerOutput:
        async with self.main_database.master().acquire() as conn:  # type: GinoConnection
            stmt = stripe_customers.table.select().where(
                stripe_customers.id == request.id
            )
            row = await conn.execution_options(
                timeout=self.main_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return GetStripeCustomerOutput.from_orm(row)

    async def update_stripe_customer(
        self,
        request_set: UpdateStripeCustomerSetInput,
        request_where: UpdateStripeCustomerWhereInput,
    ) -> UpdateStripeCustomerOutput:
        async with self.main_database.master().acquire() as conn:  # type: GinoConnection
            stmt = (
                stripe_customers.table.update()
                .where(stripe_customers.id == request_where.id)
                .values(request_set.dict(skip_defaults=True))
                .returning(*stripe_customers.table.columns.values())
            )
            row = await conn.execution_options(
                timeout=self.main_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return UpdateStripeCustomerOutput.from_orm(row)
