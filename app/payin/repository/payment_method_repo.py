from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

from typing_extensions import final

from app.commons import tracing
from app.commons.context.logger import get_logger
from app.commons.database.model import DBEntity, DBRequestModel

###########################################################
# PgpPaymentMethod DBEntity and CRUD operations           #
###########################################################
from app.payin.models.maindb import stripe_cards
from app.payin.models.paymentdb import pgp_payment_methods
from app.payin.repository.base import PayinDBRepository

log = get_logger(__name__)


class PgpPaymentMethodDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: str
    pgp_code: str
    pgp_resource_id: str
    payer_id: Optional[str] = None
    pgp_card_id: Optional[str] = None
    legacy_consumer_id: Optional[str] = None
    object: Optional[str] = None
    type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    attached_at: Optional[datetime] = None
    detached_at: Optional[datetime] = None


class InsertPgpPaymentMethodInput(PgpPaymentMethodDbEntity):
    pass


class GetPgpPaymentMethodByPaymentMethodIdInput(DBRequestModel):
    payment_method_id: str


class GetPgpPaymentMethodByPgpResourceIdInput(DBRequestModel):
    pgp_resource_id: str


class GetPgpPaymentMethodByIdInput(DBRequestModel):
    id: Optional[str]
    pgp_resource_id: Optional[str]


class DeletePgpPaymentMethodByIdSetInput(DBRequestModel):
    detached_at: datetime
    deleted_at: datetime
    updated_at: datetime


class DeletePgpPaymentMethodByIdWhereInput(DBRequestModel):
    id: str


###########################################################
# StripeCard DBEntity and CRUD operations                 #
###########################################################
class StripeCardDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: Optional[int] = None  # DB incremental id
    stripe_id: str
    fingerprint: str
    last4: str
    dynamic_last4: str
    exp_month: str
    exp_year: str
    type: str
    country_of_origin: Optional[str] = None
    zip_code: Optional[str] = None
    created_at: Optional[datetime] = None
    removed_at: Optional[datetime] = None
    is_scanned: Optional[bool] = None
    dd_fingerprint: Optional[str] = None
    active: bool
    consumer_id: Optional[int] = None
    stripe_customer_id: Optional[int] = None
    external_stripe_customer_id: Optional[str] = None
    tokenization_method: Optional[str] = None
    address_line1_check: Optional[str] = None
    address_zip_check: Optional[str] = None
    validation_card_id: Optional[int] = None


class InsertStripeCardInput(StripeCardDbEntity):
    pass


class GetStripeCardByStripeIdInput(DBRequestModel):
    stripe_id: str


class GetStripeCardByIdInput(DBRequestModel):
    id: int


class DeleteStripeCardByIdSetInput(DBRequestModel):
    removed_at: datetime


class DeleteStripeCardByIdWhereInput(DBRequestModel):
    id: int


class PaymentMethodRepositoryInterface:
    """
    PaymentMethod repository interface class that exposes complicated CRUD operations APIs for business layer.
    """

    @abstractmethod
    async def insert_payment_method_and_stripe_card(
        self, pm_input: InsertPgpPaymentMethodInput, sc_input: InsertStripeCardInput
    ) -> Tuple[PgpPaymentMethodDbEntity, StripeCardDbEntity]:
        ...

    @abstractmethod
    async def get_pgp_payment_method_by_payment_method_id(
        self, input: GetPgpPaymentMethodByPaymentMethodIdInput
    ) -> Optional[PgpPaymentMethodDbEntity]:
        ...

    @abstractmethod
    async def get_pgp_payment_method_by_pgp_resource_id(
        self, input: GetPgpPaymentMethodByPgpResourceIdInput
    ) -> Optional[PgpPaymentMethodDbEntity]:
        ...

    @abstractmethod
    async def get_stripe_card_by_stripe_id(
        self, input: GetStripeCardByStripeIdInput
    ) -> Optional[StripeCardDbEntity]:
        ...

    @abstractmethod
    async def get_stripe_card_by_id(
        self, input: GetStripeCardByIdInput
    ) -> Optional[StripeCardDbEntity]:
        ...


@tracing.set_repository_name("payment_method", only_trackable=False)
@final
@dataclass
class PaymentMethodRepository(PaymentMethodRepositoryInterface, PayinDBRepository):
    """
    PaymentMethod repository class that exposes complicated CRUD operations APIs for business layer.
    """

    async def insert_payment_method_and_stripe_card(
        self, pm_input: InsertPgpPaymentMethodInput, sc_input: InsertStripeCardInput
    ) -> Tuple[PgpPaymentMethodDbEntity, StripeCardDbEntity]:
        maindb_conn = self.main_database.master()
        paymentdb_conn = self.payment_database.master()
        async with maindb_conn.transaction(), paymentdb_conn.transaction():
            # insert object into stripe_card table
            try:
                log.info(
                    "[insert_payment_method_and_stripe_card] ready to insert stripe_card table"
                )
                stmt = (
                    stripe_cards.table.insert()
                    .values(sc_input.dict(skip_defaults=True))
                    .returning(*stripe_cards.table.columns.values())
                )
                row = await maindb_conn.fetch_one(stmt)
                assert row
                sc_output = StripeCardDbEntity.from_row(row)
                log.info(
                    "[insert_payment_method_and_stripe_card] insert stripe_card table completed."
                )
            except Exception as e:
                log.error(
                    "[insert_payment_method_and_stripe_card] exception caught by inserting stripe_card table. rollback from stripe_card table",
                    e,
                )
                raise e

            # insert object into pgp_payment_methods table
            try:
                log.info(
                    "[insert_payment_method_and_stripe_card] ready to insert pgp_payment_methods table"
                )
                stmt = (
                    pgp_payment_methods.table.insert()
                    .values(pm_input.dict(skip_defaults=True))
                    .returning(*pgp_payment_methods.table.columns.values())
                )
                row = await self.payment_database.master().fetch_one(stmt)
                assert row
                pm_output = PgpPaymentMethodDbEntity.from_row(row)
                log.info(
                    "[insert_payment_method_and_stripe_card] insert pgp_payment_methods table completed."
                )
            except Exception as e:
                log.error(
                    "[insert_payment_method_and_stripe_card] exception caught by inserting pgp_customers table. rollback both stripe_customer and pgp_payment_method",
                    e,
                )
                raise e

            return pm_output, sc_output

    async def get_pgp_payment_method_by_payment_method_id(
        self, input: GetPgpPaymentMethodByPaymentMethodIdInput
    ) -> Optional[PgpPaymentMethodDbEntity]:
        stmt = pgp_payment_methods.table.select().where(
            pgp_payment_methods.id == input.payment_method_id
        )
        row = await self.payment_database.replica().fetch_one(stmt)
        return PgpPaymentMethodDbEntity.from_row(row) if row else None

    async def get_pgp_payment_method_by_pgp_resource_id(
        self, input: GetPgpPaymentMethodByPgpResourceIdInput
    ) -> Optional[PgpPaymentMethodDbEntity]:
        stmt = pgp_payment_methods.table.select().where(
            pgp_payment_methods.pgp_resource_id == input.pgp_resource_id
        )
        row = await self.payment_database.replica().fetch_one(stmt)
        return PgpPaymentMethodDbEntity.from_row(row) if row else None

    async def get_pgp_payment_method_by_id(
        self, input: GetPgpPaymentMethodByIdInput
    ) -> Optional[PgpPaymentMethodDbEntity]:
        if input.id:
            stmt = pgp_payment_methods.table.select().where(
                pgp_payment_methods.id == input.id
            )
        else:
            stmt = pgp_payment_methods.table.select().where(
                pgp_payment_methods.pgp_resource_id == input.pgp_resource_id
            )
            row = await self.payment_database.replica().fetch_one(stmt)
        return PgpPaymentMethodDbEntity.from_row(row) if row else None

    async def delete_pgp_payment_method_by_id(
        self,
        input_set: DeletePgpPaymentMethodByIdSetInput,
        input_where: DeletePgpPaymentMethodByIdWhereInput,
    ) -> Optional[PgpPaymentMethodDbEntity]:
        stmt = (
            pgp_payment_methods.table.update()
            .where(pgp_payment_methods.id == input_where.id)
            .values(input_set.dict(skip_defaults=True))
            .returning(*pgp_payment_methods.table.columns.values())
        )
        row = await self.payment_database.master().fetch_one(stmt)
        return PgpPaymentMethodDbEntity.from_row(row) if row else None

    async def get_stripe_card_by_stripe_id(
        self, input: GetStripeCardByStripeIdInput
    ) -> Optional[StripeCardDbEntity]:
        stmt = stripe_cards.table.select().where(
            stripe_cards.stripe_id == input.stripe_id
        )
        row = await self.main_database.replica().fetch_one(stmt)
        return StripeCardDbEntity.from_row(row) if row else None

    async def get_stripe_card_by_id(
        self, input: GetStripeCardByIdInput
    ) -> Optional[StripeCardDbEntity]:
        stmt = stripe_cards.table.select().where(stripe_cards.id == input.id)
        row = await self.main_database.replica().fetch_one(stmt)
        return StripeCardDbEntity.from_row(row) if row else None

    async def delete_stripe_card_by_id(
        self,
        input_set: DeleteStripeCardByIdSetInput,
        input_where: DeleteStripeCardByIdWhereInput,
    ):
        stmt = (
            stripe_cards.table.update()
            .where(stripe_cards.id == input_where.id)
            .values(input_set.dict(skip_defaults=True))
            .returning(*stripe_cards.table.columns.values())
        )
        row = await self.main_database.master().fetch_one(stmt)
        return StripeCardDbEntity.from_row(row) if row else None
