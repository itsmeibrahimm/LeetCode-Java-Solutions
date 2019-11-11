from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List

import pytz
from sqlalchemy import and_, desc
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.payout.core.errors import InstantPayoutCreatePayoutError
from app.payout.core.instant_payout.models import (
    InstantPayoutStatusType,
    CreatePayoutsRequest,
    CreatePayoutsResponse,
)
from app.payout.core.instant_payout.utils import _gen_token
from app.payout.models import TransactionTargetType, PayoutType
from app.payout.repository.bankdb.base import PayoutBankDBRepository
from app.payout.repository.bankdb.model.payout import Payout, PayoutCreate, PayoutUpdate
from app.payout.repository.bankdb.model import payouts, transactions
from app.payout.repository.bankdb.model.transaction import (
    TransactionCreateDBEntity,
    TransactionUpdateDBEntity,
    TransactionDBEntity,
)


class PayoutRepositoryInterface(ABC):
    @abstractmethod
    async def create_payout(self, data: PayoutCreate) -> Payout:
        pass

    @abstractmethod
    async def get_payout_by_id(self, payout_id: int) -> Optional[Payout]:
        pass

    @abstractmethod
    async def update_payout_by_id(
        self, payout_id: int, data: PayoutUpdate
    ) -> Optional[Payout]:
        pass

    @abstractmethod
    async def list_payout_by_payout_account_id(
        self,
        payout_account_id: int,
        offset: int,
        statuses: Optional[List[InstantPayoutStatusType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = 10,
    ) -> List[Payout]:
        pass

    @abstractmethod
    async def create_payout_and_attach_to_transactions(
        self, request: CreatePayoutsRequest
    ) -> CreatePayoutsResponse:
        pass


@final
@tracing.track_breadcrumb(repository_name="payout")
class PayoutRepository(PayoutBankDBRepository, PayoutRepositoryInterface):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_payout(self, data: PayoutCreate) -> Payout:
        ts_now = datetime.utcnow()
        stmt = (
            payouts.table.insert()
            .values(data.dict(skip_defaults=True), created_at=ts_now, updated_at=ts_now)
            .returning(*payouts.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return Payout.from_row(row)

    async def get_payout_by_id(self, payout_id: int) -> Optional[Payout]:
        stmt = payouts.table.select().where(payouts.id == payout_id)
        row = await self._database.replica().fetch_one(stmt)
        return Payout.from_row(row) if row else None

    async def update_payout_by_id(
        self, payout_id: int, data: PayoutUpdate
    ) -> Optional[Payout]:
        stmt = (
            payouts.table.update()
            .where(payouts.id == payout_id)
            .values(
                data.dict_after_json_to_string(skip_defaults=True),
                updated_at=datetime.utcnow(),
            )
            .returning(*payouts.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        return Payout.from_row(row) if row else None

    async def list_payout_by_payout_account_id(
        self,
        payout_account_id: int,
        offset: int,
        statuses: Optional[List[InstantPayoutStatusType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = 10,
    ):
        override_stmt_timeout_in_ms = 10000
        override_stmt_timeout_stmt = "SET LOCAL statement_timeout = {};".format(
            override_stmt_timeout_in_ms
        )
        async with self._database.master().transaction() as tx:
            connection = tx.connection()

            # 1. overwrite timeout
            await connection.execute(override_stmt_timeout_stmt)

            # 2. Query payout
            conditions = [payouts.payment_account_id == payout_account_id]
            if statuses:
                conditions.append(payouts.status.in_(statuses))
            if start_time:
                conditions.append(payouts.created_at.__ge__(start_time))
            if end_time:
                conditions.append(payouts.created_at.__le__(end_time))

            stmt = (
                payouts.table.select()
                .where(and_(*conditions))
                .order_by(desc(payouts.id))
                .offset(offset)
                .limit(limit)
            )
            rows = await connection.fetch_all(stmt)
            if rows:
                return [Payout.from_row(row) for row in rows]
            else:
                return []

    async def create_payout_and_attach_to_transactions(
        self, request: CreatePayoutsRequest
    ) -> CreatePayoutsResponse:
        override_stmt_timeout_in_ms = 10000
        override_stmt_timeout_stmt = "SET LOCAL statement_timeout = {};".format(
            override_stmt_timeout_in_ms
        )
        ts_now = datetime.utcnow()
        async with self._database.master().transaction() as tx:
            connection = tx.connection()
            # 1. overwrite timeout
            await connection.execute(override_stmt_timeout_stmt)

            # 2. Create fee transaction
            transaction_create = TransactionCreateDBEntity(
                amount=-request.fee,
                # Put amount_paid as 0 to pass Pydantic validation
                amount_paid=0,
                currency=request.currency.upper(),
                payment_account_id=request.payout_account_id,
                target_type=TransactionTargetType.PAYOUT_FEE,
                target_id=None,
                idempotency_key="instant-payout-fee-{}".format(request.idempotency_key),
            )
            create_fee_transaction_stmt = (
                transactions.table.insert()
                .values(
                    transaction_create.dict(skip_defaults=True),
                    created_at=ts_now,
                    updated_at=ts_now,
                )
                .returning(*transactions.table.columns.values())
            )
            row = await connection.fetch_one(create_fee_transaction_stmt)
            assert row is not None
            fee_transaction = TransactionDBEntity.from_row(row)

            # 3. Create Payout
            payout_create = PayoutCreate(
                amount=request.amount - request.fee,
                payment_account_id=request.payout_account_id,
                status=InstantPayoutStatusType.NEW,
                currency=request.currency.upper(),
                fee=request.fee,
                type=PayoutType.INSTANT,
                idempotency_key=request.idempotency_key,
                payout_method_id=request.payout_method_id,
                transaction_ids=request.transaction_ids,
                token=_gen_token(),
                fee_transaction_id=fee_transaction.id,
            )
            create_payout_stmt = (
                payouts.table.insert()
                .values(
                    payout_create.dict(skip_defaults=True),
                    created_at=ts_now,
                    updated_at=ts_now,
                )
                .returning(*payouts.table.columns.values())
            )
            row = await connection.fetch_one(create_payout_stmt)
            assert row is not None
            payout = Payout.from_row(row)

            # 4. Update transaction payout ids
            data = TransactionUpdateDBEntity(payout_id=payout.id)
            all_transaction_ids = request.transaction_ids + [fee_transaction.id]
            stmt = (
                transactions.table.update()
                .where(
                    and_(
                        transactions.id.in_(all_transaction_ids),
                        transactions.payout_id.is_(None),
                    )
                )
                .values(data.dict(skip_defaults=True), updated_at=datetime.utcnow())
                .returning(*transactions.table.columns.values())
            )
            rows = await connection.fetch_all(stmt)
            all_transactions = (
                [TransactionDBEntity.from_row(row) for row in rows] if rows else []
            )

            # 5. Verify updated number of transactions matches number of input transaction
            try:
                assert len(all_transactions) == len(all_transaction_ids)
            except AssertionError as e:
                raise InstantPayoutCreatePayoutError(
                    error_message="Updated transaction count not match."
                ) from e

            # 6. Verify sum of transaction amount matches payout amount
            try:
                assert (
                    sum([transaction.amount for transaction in all_transactions])
                    == payout.amount
                )
            except AssertionError as e:
                raise InstantPayoutCreatePayoutError(
                    error_message="Updated transaction amount not match payout amount."
                ) from e

            return CreatePayoutsResponse(
                payout_id=payout.id,
                amount=payout.amount,
                fee=payout.fee,
                created_at=payout.created_at.replace(tzinfo=pytz.UTC),
            )
