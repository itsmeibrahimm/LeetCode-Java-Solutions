import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Tuple

from sqlalchemy.sql.elements import and_
from typing_extensions import final

from app.commons import tracing
from app.commons.database.client.interface import DBConnection
from app.commons.database.infra import DB
from app.payout.repository.bankdb.base import PayoutBankDBRepository
from app.payout.repository.bankdb.model import payout_method, payout_card
from app.payout.repository.bankdb.model.payout_card import PayoutCard, PayoutCardCreate
from app.payout.repository.bankdb.model.payout_method import (
    PayoutMethod,
    PayoutMethodMiscellaneousCreate,
    PayoutMethodCreate,
)


class PayoutMethodMiscellaneousRepositoryInterface(ABC):
    @abstractmethod
    async def unset_default_and_create_payout_method_and_payout_card(
        self, data: PayoutMethodMiscellaneousCreate
    ) -> Tuple[PayoutMethod, PayoutCard]:
        pass


@final
@tracing.track_breadcrumb(repository_name="payout_card")
class PayoutMethodMiscellaneousRepository(
    PayoutBankDBRepository, PayoutMethodMiscellaneousRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def unset_default_and_create_payout_method_and_payout_card(
        self, data: PayoutMethodMiscellaneousCreate
    ) -> Tuple[PayoutMethod, PayoutCard]:
        async with self._database.master().acquire() as connection:  # type: DBConnection
            try:
                created_payout_method, created_payout_card = await self.execute_unset_default_and_create_payout_method_and_payout_card(
                    data=data, db_connection=connection
                )
                return created_payout_method, created_payout_card
            except Exception as e:
                raise e

    async def execute_unset_default_and_create_payout_method_and_payout_card(
        self, data: PayoutMethodMiscellaneousCreate, db_connection: DBConnection
    ) -> Tuple[PayoutMethod, PayoutCard]:
        async with db_connection.transaction():
            update_payout_method_stmt = (
                payout_method.table.update()
                .where(
                    and_(
                        payout_method.payment_account_id == data.payout_account_id,
                        payout_method.deleted_at.is_(None),
                        payout_method.type == data.payout_method_type,
                    )
                )
                .values(is_default=False)
                .returning(*payout_method.table.columns.values())
            )
            await db_connection.fetch_all(update_payout_method_stmt)

            ts_now = datetime.utcnow()
            payout_method_create = PayoutMethodCreate(
                type=data.card.object,
                currency=data.card.currency,
                country=data.card.country,
                payment_account_id=data.payout_account_id,
                is_default=True,
                token=uuid.uuid4(),
            )
            create_payout_method_stmt = (
                payout_method.table.insert()
                .values(
                    payout_method_create.dict(skip_defaults=True),
                    created_at=ts_now,
                    updated_at=ts_now,
                )
                .returning(*payout_method.table.columns.values())
            )
            row = await db_connection.fetch_one(create_payout_method_stmt)
            assert row is not None
            created_payout_method = PayoutMethod.from_row(row)

            payout_card_create = PayoutCardCreate(
                stripe_card_id=data.card.id,
                last4=data.card.last4,
                brand=data.card.brand,
                exp_month=data.card.exp_month,
                exp_year=data.card.exp_year,
                fingerprint=data.card.fingerprint,
                id=created_payout_method.id,
                created_at=created_payout_method.created_at,
                updated_at=created_payout_method.updated_at,
            )
            create_payout_card_stmt = (
                payout_card.table.insert()
                .values(payout_card_create.dict(skip_defaults=True))
                .returning(*payout_card.table.columns.values())
            )
            row = await db_connection.fetch_one(create_payout_card_stmt)
            assert row is not None
            created_payout_card = PayoutCard.from_row(row)
            return created_payout_method, created_payout_card
