from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List

from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql.elements import and_
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.repository.bankdb.base import PayoutBankDBRepository
from app.payout.repository.bankdb.model import payout_method
from app.payout.repository.bankdb.model.payout_method import (
    PayoutMethodCreate,
    PayoutMethod,
    PayoutMethodUpdate,
)


class PayoutMethodRepositoryInterface(ABC):
    @abstractmethod
    async def create_payout_method(self, data: PayoutMethodCreate) -> PayoutMethod:
        pass

    @abstractmethod
    async def get_payout_method_by_id(
        self, payout_method_id: int
    ) -> Optional[PayoutMethod]:
        pass

    @abstractmethod
    async def list_payout_cards_by_payout_account_id(
        self, payout_account_id: int
    ) -> List[PayoutMethod]:
        pass

    @abstractmethod
    async def update_payout_method_deleted_at(
        self, token: UUID, data: PayoutMethodUpdate
    ) -> Optional[PayoutMethod]:
        pass


@final
@tracing.track_breadcrumb(repository_name="payout_card")
class PayoutMethodRepository(PayoutBankDBRepository, PayoutMethodRepositoryInterface):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_payout_method(self, data: PayoutMethodCreate) -> PayoutMethod:
        ts_now = datetime.utcnow()
        stmt = (
            payout_method.table.insert()
            .values(data.dict(skip_defaults=True), created_at=ts_now, updated_at=ts_now)
            .returning(*payout_method.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return PayoutMethod.from_row(row)

    async def get_payout_method_by_id(
        self, payout_method_id: int
    ) -> Optional[PayoutMethod]:
        stmt = payout_method.table.select().where(payout_method.id == payout_method_id)
        row = await self._database.replica().fetch_one(stmt)
        return PayoutMethod.from_row(row) if row else None

    async def list_payout_cards_by_payout_account_id(
        self, payout_account_id: int
    ) -> List[PayoutMethod]:
        stmt = (
            payout_method.table.select()
            .order_by(desc(payout_method.id))  # set order_by pk desc as default for now
            .where(
                and_(
                    payout_method.payment_account_id == payout_account_id,
                    payout_method.deleted_at.is_(None),
                )
            )
        )

        rows = await self._database.replica().fetch_all(stmt)
        if rows:
            return [PayoutMethod.from_row(row) for row in rows]
        else:
            return []

    async def update_payout_method_deleted_at(
        self, token: UUID, data: PayoutMethodUpdate
    ) -> Optional[PayoutMethod]:
        stmt = (
            payout_method.table.update()
            .where(
                and_(
                    payout_method.token == str(token),
                    payout_method.deleted_at.is_(None),
                )
            )
            .values(
                data.dict_after_json_to_string(skip_defaults=True),
                updated_at=datetime.utcnow(),
            )
            .returning(*payout_method.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        return PayoutMethod.from_row(row) if row else None
