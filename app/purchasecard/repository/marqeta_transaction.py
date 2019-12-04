from typing_extensions import final
from typing import Optional

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.repository.base import PurchaseCardMainDBRepository
from app.purchasecard.models.maindb import marqeta_transactions
from app.purchasecard.models.maindb.marqeta_transaction import (
    MarqetaTransactionDBEntity,
)


@final
@tracing.track_breadcrumb(repository_name="marqeta_transaction")
class MarqetaTransactionRepository(PurchaseCardMainDBRepository):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def update_marqeta_transaction_timeout_by_token(
        self, transaction_token: str, timed_out: bool
    ) -> MarqetaTransactionDBEntity:
        stmt = (
            marqeta_transactions.table.update()
            .where(marqeta_transactions.token == transaction_token)
            .values(timed_out=timed_out)
            .returning(*marqeta_transactions.table.columns.values())
        )
        marqeta_transaction = await self._database.master().fetch_one(stmt)
        assert marqeta_transaction
        return MarqetaTransactionDBEntity.from_row(marqeta_transaction)

    async def create_marqeta_transaction(
        self, data: MarqetaTransactionDBEntity
    ) -> MarqetaTransactionDBEntity:
        stmt = (
            marqeta_transactions.table.insert()
            .values(data.dict())
            .returning(*marqeta_transactions.table.columns.values())
        )
        marqeta_transaction = await self._database.master().fetch_one(stmt)
        assert marqeta_transaction
        return MarqetaTransactionDBEntity.from_row(marqeta_transaction)

    async def get_marqeta_transaction_by_token(
        self, transaction_token: str
    ) -> Optional[MarqetaTransactionDBEntity]:
        stmt = marqeta_transactions.table.select().where(
            marqeta_transactions.token == transaction_token
        )
        row = await self._database.replica().fetch_one(stmt)
        return MarqetaTransactionDBEntity.from_row(row) if row else None
