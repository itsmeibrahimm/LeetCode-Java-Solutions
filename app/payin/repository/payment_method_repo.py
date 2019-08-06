from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple

import logging

from gino import GinoConnection
from typing_extensions import final

from app.commons.database.model import DBEntity, DBRequestModel

###########################################################
# PgpPaymentMethod DBEntity and CRUD operations           #
###########################################################
from app.payin.models.maindb import stripe_cards
from app.payin.models.paymentdb import pgp_payment_methods
from app.payin.repository.base import PayinDBRepository

logger = logging.getLogger(__name__)


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


class InsertPgpPaymentMethodOutput(PgpPaymentMethodDbEntity):
    pass


class GetPgpPaymentMethodByPaymentMethodIdInput(DBRequestModel):
    payment_method_id: str


class GetPgpPaymentMethodByPgpResourceIdInput(DBRequestModel):
    pgp_resource_id: str


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


class InsertStripeCardOutput(StripeCardDbEntity):
    pass


class GetStripeCardByStripeIdInput(DBRequestModel):
    stripe_id: str


class GetStripeCardByIdInput(DBRequestModel):
    id: int


class PaymentMethodRepositoryInterface:
    """
    PaymentMethod repository interface class that exposes complicated CRUD operations APIs for business layer.
    """

    @abstractmethod
    async def insert_payment_method_and_stripe_card(
        self, pm_input: InsertPgpPaymentMethodInput, sc_input: InsertStripeCardInput
    ) -> Tuple[InsertPgpPaymentMethodOutput, InsertStripeCardOutput]:
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


@final
@dataclass
class PaymentMethodRepository(PaymentMethodRepositoryInterface, PayinDBRepository):
    """
    PaymentMethod repository class that exposes complicated CRUD operations APIs for business layer.
    """

    async def insert_payment_method_and_stripe_card(
        self, pm_input: InsertPgpPaymentMethodInput, sc_input: InsertStripeCardInput
    ) -> Tuple[InsertPgpPaymentMethodOutput, InsertStripeCardOutput]:

        # acquire connection.
        async with self.main_database.master().acquire() as maindb_conn:  # type: GinoConnection
            async with self.payment_database.master().acquire() as paymentdb_conn:  # type: GinoConnection
                # acquire maindb transaction
                async with maindb_conn.transaction() as maindb_txn:
                    # insert object into stripe_card table
                    try:
                        logger.info(
                            "[insert_payment_method_and_stripe_card] ready to insert stripe_card table"
                        )
                        stmt = (
                            stripe_cards.table.insert()
                            .values(sc_input.dict(skip_defaults=True))
                            .returning(*stripe_cards.table.columns.values())
                        )
                        row = await maindb_conn.execution_options(
                            timeout=self.main_database.STATEMENT_TIMEOUT_SEC
                        ).first(stmt)
                        sc_output = InsertStripeCardOutput.from_orm(row)
                        logger.info(
                            "[insert_payment_method_and_stripe_card] insert stripe_card table completed."
                        )
                    except Exception as e:
                        logger.error(
                            "[insert_payment_method_and_stripe_card] exception caught by inserting stripe_card table. rollback from stripe_card table",
                            e,
                        )
                        await maindb_txn.raise_rollback()
                        raise e

                    # acquire paymentdb transaction
                    async with paymentdb_conn.transaction() as paymentdb_txn:
                        # insert object into pgp_payment_methods table
                        try:
                            logger.info(
                                "[insert_payment_method_and_stripe_card] ready to insert pgp_payment_methods table"
                            )
                            stmt = (
                                pgp_payment_methods.table.insert()
                                .values(pm_input.dict(skip_defaults=True))
                                .returning(*pgp_payment_methods.table.columns.values())
                            )
                            row = await paymentdb_conn.execution_options(
                                timeout=self.payment_database.STATEMENT_TIMEOUT_SEC
                            ).first(stmt)
                            pm_output = InsertPgpPaymentMethodOutput.from_orm(row)
                            logger.info(
                                "[insert_payment_method_and_stripe_card] insert pgp_payment_methods table completed."
                            )
                        except Exception as e:
                            logger.error(
                                "[insert_payment_method_and_stripe_card] exception caught by inserting pgp_customers table. rollback both stripe_customer and pgp_payment_method",
                                e,
                            )
                            await maindb_txn.raise_rollback()
                            await paymentdb_txn.raise_rollback()
                            raise e

        return pm_output, sc_output

    async def get_pgp_payment_method_by_payment_method_id(
        self, input: GetPgpPaymentMethodByPaymentMethodIdInput
    ) -> Optional[PgpPaymentMethodDbEntity]:
        async with self.payment_database.master().acquire() as conn:  # type: GinoConnection
            stmt = pgp_payment_methods.table.select().where(
                pgp_payment_methods.id == input.payment_method_id
            )
            row = await conn.execution_options(
                timeout=self.payment_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return PgpPaymentMethodDbEntity.from_orm(row) if row else None

    async def get_pgp_payment_method_by_pgp_resource_id(
        self, input: GetPgpPaymentMethodByPgpResourceIdInput
    ) -> Optional[PgpPaymentMethodDbEntity]:
        async with self.payment_database.master().acquire() as conn:  # type: GinoConnection
            stmt = pgp_payment_methods.table.select().where(
                pgp_payment_methods.pgp_resource_id == input.pgp_resource_id
            )
            row = await conn.execution_options(
                timeout=self.payment_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return PgpPaymentMethodDbEntity.from_orm(row) if row else None

    async def get_stripe_card_by_stripe_id(
        self, input: GetStripeCardByStripeIdInput
    ) -> Optional[StripeCardDbEntity]:
        async with self.main_database.master().acquire() as conn:  # type: GinoConnection
            stmt = stripe_cards.table.select().where(
                stripe_cards.stripe_id == input.stripe_id
            )
            row = await conn.execution_options(
                timeout=self.main_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return StripeCardDbEntity.from_orm(row) if row else None

    async def get_stripe_card_by_id(
        self, input: GetStripeCardByIdInput
    ) -> Optional[StripeCardDbEntity]:
        async with self.main_database.master().acquire() as conn:  # type: GinoConnection
            stmt = stripe_cards.table.select().where(stripe_cards.id == input.id)
            row = await conn.execution_options(
                timeout=self.main_database.STATEMENT_TIMEOUT_SEC
            ).first(stmt)
            return StripeCardDbEntity.from_orm(row) if row else None
