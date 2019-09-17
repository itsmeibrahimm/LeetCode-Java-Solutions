from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select, and_
from typing_extensions import final

from app.commons import tracing
from app.commons.database.model import DBRequestModel, DBEntity
from app.payin.core.types import MixedUuidStrType
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

    id: UUID
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


class GetPayerByIdInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    id: Optional[MixedUuidStrType]
    legacy_stripe_customer_id: Optional[str]
    dd_payer_id: Optional[str]


class GetPayerByDDPayerIdAndTypeInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    dd_payer_id: str
    payer_type: str


###########################################################
# PgpCustomer DBEntity and CRUD operations                #
###########################################################
class PgpCustomerDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: UUID
    payer_id: UUID
    pgp_resource_id: str
    currency: Optional[str] = None
    pgp_code: Optional[str] = None
    legacy_id: Optional[int] = None
    account_balance: Optional[int] = None
    default_payment_method_id: Optional[str] = None
    legacy_default_source_id: Optional[str] = None
    legacy_default_card_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class InsertPgpCustomerInput(PgpCustomerDbEntity):
    pass


class GetPgpCustomerInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    payer_id: str
    pgp_code: Optional[str]


class UpdatePgpCustomerSetInput(BaseModel):
    """
    The variable name must be consistent with DB table column name
    """

    updated_at: datetime
    currency: Optional[str]
    default_payment_method_id: Optional[str]
    legacy_default_source_id: Optional[str]
    legacy_default_card_id: Optional[str]


class UpdatePgpCustomerWhereInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    id: UUID


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


class GetStripeCustomerByIdInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    id: int


class GetStripeCustomerByStripeIdInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    stripe_id: str


class UpdateStripeCustomerSetInput(BaseModel):
    """
    The variable name must be consistent with DB table column name
    """

    default_card: Optional[str]
    default_source: Optional[str]


class UpdateStripeCustomerWhereInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    id: int


class UpdateStripeCustomerByStripeIdWhereInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    stripe_id: str


class PayerRepositoryInterface:
    """
    Payer repository interface class that exposes complicated CRUD operations APIs for business layer.
    """

    @abstractmethod
    async def insert_payer(self, request: InsertPayerInput) -> PayerDbEntity:
        ...

    @abstractmethod
    async def insert_payer_and_pgp_customer(
        self, payer_input: InsertPayerInput, pgp_customer_input: InsertPgpCustomerInput
    ) -> Tuple[PayerDbEntity, PgpCustomerDbEntity]:
        ...

    @abstractmethod
    async def get_payer_by_dd_payer_id_and_payer_type(
        self, input: GetPayerByDDPayerIdAndTypeInput
    ) -> Optional[PayerDbEntity]:
        ...

    @abstractmethod
    async def get_payer_by_id(
        self, request: GetPayerByIdInput
    ) -> Optional[PayerDbEntity]:
        ...

    @abstractmethod
    async def get_payer_and_pgp_customer_by_id(
        self, input: GetPayerByIdInput
    ) -> Tuple[Optional[PayerDbEntity], Optional[PgpCustomerDbEntity]]:
        ...

    @abstractmethod
    async def insert_pgp_customer(
        self, request: InsertPgpCustomerInput
    ) -> PgpCustomerDbEntity:
        ...

    @abstractmethod
    async def get_pgp_customer(
        self, request: GetPgpCustomerInput
    ) -> PgpCustomerDbEntity:
        ...

    @abstractmethod
    async def update_pgp_customer(
        self,
        request_set: UpdatePgpCustomerSetInput,
        request_where: UpdatePgpCustomerWhereInput,
    ) -> PgpCustomerDbEntity:
        ...

    @abstractmethod
    async def insert_stripe_customer(
        self, request: InsertStripeCustomerInput
    ) -> StripeCustomerDbEntity:
        ...

    @abstractmethod
    async def get_stripe_customer_by_id(
        self, request: GetStripeCustomerByIdInput
    ) -> StripeCustomerDbEntity:
        ...

    @abstractmethod
    async def get_stripe_customer_by_stripe_id(
        self, request: GetStripeCustomerByStripeIdInput
    ) -> StripeCustomerDbEntity:
        ...

    @abstractmethod
    async def update_stripe_customer(
        self,
        request_set: UpdateStripeCustomerSetInput,
        request_where: UpdateStripeCustomerWhereInput,
    ) -> StripeCustomerDbEntity:
        ...

    @abstractmethod
    async def update_stripe_customer_by_stripe_id(
        self,
        request_set: UpdateStripeCustomerSetInput,
        request_where: UpdateStripeCustomerByStripeIdWhereInput,
    ) -> StripeCustomerDbEntity:
        ...


@final
@tracing.track_breadcrumb(repository_name="payer")
@dataclass
class PayerRepository(PayerRepositoryInterface, PayinDBRepository):
    """
    Payer repository class that exposes complicated CRUD operations APIs for business layer.
    """

    async def insert_payer(self, request: InsertPayerInput) -> PayerDbEntity:
        stmt = (
            payers.table.insert()
            .values(request.dict(skip_defaults=True))
            .returning(*payers.table.columns.values())
        )
        row = await self.payment_database.master().fetch_one(stmt)
        return PayerDbEntity.from_row(row)  # type: ignore

    async def insert_payer_and_pgp_customer(
        self, payer_input: InsertPayerInput, pgp_customer_input: InsertPgpCustomerInput
    ) -> Tuple[PayerDbEntity, PgpCustomerDbEntity]:
        paymentdb_conn = self.payment_database.master()
        async with paymentdb_conn.transaction():
            # insert payers table
            stmt = (
                payers.table.insert()
                .values(payer_input.dict(skip_defaults=True))
                .returning(*payers.table.columns.values())
            )
            payer_row = await self.payment_database.master().fetch_one(stmt)
            # insert pgp_customers table
            stmt = (
                pgp_customers.table.insert()
                .values(pgp_customer_input.dict(skip_defaults=True))
                .returning(*pgp_customers.table.columns.values())
            )
            pgp_cus_row = await self.payment_database.master().fetch_one(stmt)
            if not payer_row or not pgp_cus_row:
                return Tuple[None, None]
            return (
                PayerDbEntity.from_row(payer_row),
                PgpCustomerDbEntity.from_row(pgp_cus_row),
            )

    async def get_payer_by_dd_payer_id_and_payer_type(
        self, input: GetPayerByDDPayerIdAndTypeInput
    ) -> Optional[PayerDbEntity]:
        stmt = payers.table.select().where(
            and_(
                payers.dd_payer_id == input.dd_payer_id,
                payers.payer_type == input.payer_type,
            )
        )
        row = await self.payment_database.replica().fetch_one(stmt)
        return PayerDbEntity.from_row(row) if row else None

    async def get_payer_by_id(
        self, request: GetPayerByIdInput
    ) -> Optional[PayerDbEntity]:
        if request.id:
            stmt = payers.table.select().where(payers.id == request.id)
        elif request.legacy_stripe_customer_id:
            stmt = payers.table.select().where(
                payers.legacy_stripe_customer_id == request.legacy_stripe_customer_id
            )
        else:
            stmt = payers.table.select().where(
                payers.dd_payer_id == request.dd_payer_id
            )
        row = await self.payment_database.replica().fetch_one(stmt)
        return PayerDbEntity.from_row(row) if row else None

    async def get_payer_and_pgp_customer_by_id(
        self, input: GetPayerByIdInput
    ) -> Tuple[Optional[PayerDbEntity], Optional[PgpCustomerDbEntity]]:
        join_stmt = payers.table.join(
            pgp_customers.table, payers.id == pgp_customers.payer_id
        )
        if input.id:
            stmt = (
                select([payers.table, pgp_customers.table], use_labels=True)
                .select_from(join_stmt)
                .where(payers.id == input.id)
            )
        elif input.dd_payer_id:
            stmt = (
                select([payers.table, pgp_customers.table], use_labels=True)
                .select_from(join_stmt)
                .where(payers.dd_payer_id == input.dd_payer_id)
            )
        elif input.legacy_stripe_customer_id:
            stmt = (
                select([payers.table, pgp_customers.table], use_labels=True)
                .select_from(join_stmt)
                .where(
                    payers.legacy_stripe_customer_id == input.legacy_stripe_customer_id
                )
            )
        row = await self.payment_database.replica().fetch_one(stmt)
        if not row:
            return None, None
        return (
            PayerDbEntity.from_row(payers._extract_columns_from_row_record(row)),
            PgpCustomerDbEntity.from_row(
                pgp_customers._extract_columns_from_row_record(row)
            ),
        )

    async def insert_pgp_customer(
        self, request: InsertPgpCustomerInput
    ) -> PgpCustomerDbEntity:
        stmt = (
            pgp_customers.table.insert()
            .values(request.dict(skip_defaults=True))
            .returning(*pgp_customers.table.columns.values())
        )
        row = await self.payment_database.master().fetch_one(stmt)
        return PgpCustomerDbEntity.from_row(row) if row else None

    async def get_pgp_customer(
        self, request: GetPgpCustomerInput
    ) -> PgpCustomerDbEntity:
        stmt = pgp_customers.table.select().where(
            pgp_customers.payer_id == request.payer_id
        )
        row = await self.payment_database.replica().fetch_one(stmt)
        return PgpCustomerDbEntity.from_row(row) if row else None

    async def update_pgp_customer(
        self,
        request_set: UpdatePgpCustomerSetInput,
        request_where: UpdatePgpCustomerWhereInput,
    ) -> PgpCustomerDbEntity:
        stmt = (
            pgp_customers.table.update()
            .where(pgp_customers.id == request_where.id)
            .values(request_set.dict(skip_defaults=True))
            .returning(*pgp_customers.table.columns.values())
        )
        row = await self.payment_database.master().fetch_one(stmt)
        return PgpCustomerDbEntity.from_row(row) if row else None

    async def insert_stripe_customer(
        self, request: InsertStripeCustomerInput
    ) -> StripeCustomerDbEntity:
        stmt = (
            stripe_customers.table.insert()
            .values(request.dict(skip_defaults=True))
            .returning(*stripe_customers.table.columns.values())
        )
        row = await self.main_database.master().fetch_one(stmt)
        return StripeCustomerDbEntity.from_row(row) if row else None

    async def get_stripe_customer_by_id(
        self, request: GetStripeCustomerByIdInput
    ) -> StripeCustomerDbEntity:
        stmt = stripe_customers.table.select().where(stripe_customers.id == request.id)
        row = await self.main_database.replica().fetch_one(stmt)
        return StripeCustomerDbEntity.from_row(row) if row else None

    async def get_stripe_customer_by_stripe_id(
        self, request: GetStripeCustomerByStripeIdInput
    ) -> StripeCustomerDbEntity:
        stmt = stripe_customers.table.select().where(
            stripe_customers.stripe_id == request.stripe_id
        )
        row = await self.main_database.replica().fetch_one(stmt)
        return StripeCustomerDbEntity.from_row(row) if row else None

    async def update_stripe_customer(
        self,
        request_set: UpdateStripeCustomerSetInput,
        request_where: UpdateStripeCustomerWhereInput,
    ) -> StripeCustomerDbEntity:
        stmt = (
            stripe_customers.table.update()
            .where(stripe_customers.id == request_where.id)
            .values(request_set.dict(skip_defaults=True))
            .returning(*stripe_customers.table.columns.values())
        )
        row = await self.main_database.master().fetch_one(stmt)
        return StripeCustomerDbEntity.from_row(row) if row else None

    async def update_stripe_customer_by_stripe_id(
        self,
        request_set: UpdateStripeCustomerSetInput,
        request_where: UpdateStripeCustomerByStripeIdWhereInput,
    ) -> StripeCustomerDbEntity:
        stmt = (
            stripe_customers.table.update()
            .where(stripe_customers.stripe_id == request_where.stripe_id)
            .values(request_set.dict(skip_defaults=True))
            .returning(*stripe_customers.table.columns.values())
        )
        row = await self.payment_database.master().fetch_one(stmt)
        return StripeCustomerDbEntity.from_row(row) if row else None
