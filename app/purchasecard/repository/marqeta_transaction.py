from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, select
from sqlalchemy.sql import text
from typing_extensions import final
from typing import Optional

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.repository.base import PurchaseCardMainDBRepository
from app.purchasecard.models.maindb import marqeta_transactions
from app.purchasecard.models.maindb.marqeta_transaction import MarqetaTransaction
from app.purchasecard.constants import MARQETA_WEBHOOK_TIMEOUT


class MarqetaTransactionRepositoryInterface(ABC):
    @abstractmethod
    async def update_marqeta_transaction_timeout_by_token(
        self, transaction_token: str, timed_out: bool
    ) -> MarqetaTransaction:
        pass

    @abstractmethod
    async def create_marqeta_transaction(
        self,
        token: str,
        amount: int,
        swiped_at: datetime,
        delivery_id: int,
        card_acceptor: str,
        currency: Optional[str] = None,
        timed_out: Optional[bool] = None,
        shift_delivery_assignment_id: Optional[int] = None,
    ) -> MarqetaTransaction:
        pass

    @abstractmethod
    async def get_marqeta_transaction_by_token(
        self, transaction_token: str
    ) -> Optional[MarqetaTransaction]:
        pass

    @abstractmethod
    async def get_funded_amount_by_delivery_id(self, delivery_id: int) -> int:
        pass


@final
@tracing.track_breadcrumb(repository_name="marqeta_transaction")
class MarqetaTransactionRepository(
    PurchaseCardMainDBRepository, MarqetaTransactionRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def update_marqeta_transaction_timeout_by_token(
        self, transaction_token: str, timed_out: bool
    ) -> MarqetaTransaction:
        stmt = (
            marqeta_transactions.table.update()
            .where(marqeta_transactions.token == transaction_token)
            .values(timed_out=timed_out)
            .returning(*marqeta_transactions.table.columns.values())
        )
        marqeta_transaction = await self._database.master().fetch_one(stmt)
        assert marqeta_transaction
        return MarqetaTransaction.from_row(marqeta_transaction)

    async def create_marqeta_transaction(
        self,
        token: str,
        amount: int,
        swiped_at: datetime,
        delivery_id: int,
        card_acceptor: str,
        currency: Optional[str] = None,
        timed_out: Optional[bool] = None,
        shift_delivery_assignment_id: Optional[int] = None,
    ) -> MarqetaTransaction:
        stmt = (
            marqeta_transactions.table.insert()
            .values(
                {
                    "token": token,
                    "amount": amount,
                    "swiped_at": swiped_at,
                    "delivery_id": delivery_id,
                    "card_acceptor": card_acceptor,
                    "currency": currency,
                    "timed_out": timed_out,
                    "shift_delivery_assignment_id": shift_delivery_assignment_id,
                }
            )
            .returning(*marqeta_transactions.table.columns.values())
        )
        marqeta_transaction = await self._database.master().fetch_one(stmt)
        assert marqeta_transaction
        return MarqetaTransaction.from_row(marqeta_transaction)

    async def get_marqeta_transaction_by_token(
        self, transaction_token: str
    ) -> Optional[MarqetaTransaction]:
        stmt = marqeta_transactions.table.select().where(
            marqeta_transactions.token == transaction_token
        )
        row = await self._database.replica().fetch_one(stmt)
        return MarqetaTransaction.from_row(row) if row else None

    async def get_funded_amount_by_delivery_id(self, delivery_id: int) -> int:
        """
            A funded amount is considered to be any approval that is one of:

            1. timed_out=False
            2. timed_out=null and swipe more than 30 seconds

            The latter case is just in case a marqeta webhook is not processed correctly. In effect
            this assumes that any swipe within the last swipe has been approved
        """
        timeout = datetime.utcnow() - timedelta(seconds=MARQETA_WEBHOOK_TIMEOUT)
        stmt = (
            select([text("SUM(amount) as total_amount")])
            .where(
                and_(
                    marqeta_transactions.delivery_id == delivery_id,
                    or_(
                        marqeta_transactions.timed_out == False,
                        and_(
                            marqeta_transactions.timed_out == None,
                            marqeta_transactions.swiped_at < timeout,
                        ),
                    ),
                )
            )
            .group_by(marqeta_transactions.delivery_id)
        )

        row = await self._database.replica().fetch_one(stmt)
        if not row:
            return 0
        # sqlalchemy would return a tuple here
        return row._row_proxy[0]  # type: ignore
