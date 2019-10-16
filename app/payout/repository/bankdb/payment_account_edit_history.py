from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, desc
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.repository.bankdb.base import PayoutBankDBRepository
from app.payout.repository.bankdb.model import payment_account_edit_history
from app.payout.repository.bankdb.model.payment_account_edit_history import (
    PaymentAccountEditHistory,
)


class PaymentAccountEditHistoryRepositoryInterface(ABC):
    @abstractmethod
    async def get_most_recent_bank_update(
        self, payment_account_id: int, within_last_timedelta: Optional[timedelta] = None
    ) -> Optional[PaymentAccountEditHistory]:
        pass


@final
@tracing.track_breadcrumb(repository_name="payment_account_edit_history")
class PaymentAccountEditHistoryRepository(
    PayoutBankDBRepository, PaymentAccountEditHistoryRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def get_most_recent_bank_update(
        self, payment_account_id: int, within_last_timedelta: Optional[timedelta] = None
    ) -> Optional[PaymentAccountEditHistory]:
        query = and_(
            payment_account_edit_history.payment_account_id.isnot(None),
            payment_account_edit_history.payment_account_id == payment_account_id,
        )
        if within_last_timedelta:
            since_date = datetime.utcnow() - within_last_timedelta
            query.clauses.append(
                payment_account_edit_history.timestamp.__gt__(since_date)
            )
        stmt = (
            payment_account_edit_history.table.select()
            .where(query)
            .order_by(desc(payment_account_edit_history.timestamp))
        )
        row = await self._database.replica().fetch_one(stmt)
        return PaymentAccountEditHistory.from_row(row) if row else None
