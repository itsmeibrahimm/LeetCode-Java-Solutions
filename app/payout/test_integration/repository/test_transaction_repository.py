import pytest
from datetime import datetime

from app.commons.database.infra import DB
from app.payout.repository.bankdb.model.transaction import (
    TransactionCreate,
    TransactionUpdate,
)
from app.payout.repository.bankdb.transaction import TransactionRepository


class TestTransactionRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def transaction_repo(self, payout_bankdb: DB) -> TransactionRepository:
        return TransactionRepository(database=payout_bankdb)

    async def test_create_get_transaction(
        self, transaction_repo: TransactionRepository
    ):
        ts_utc = datetime.utcnow()
        data = TransactionCreate(
            amount=1000,
            payment_account_id=123,
            amount_paid=800,
            currency="USD",
            created_at=ts_utc,
            updated_at=ts_utc,
        )

        created = await transaction_repo.create_transaction(data)
        assert created.id, "transaction is created, assigned an ID"

        assert created == await transaction_repo.get_transaction_by_id(
            created.id
        ), "retrieved transaction matches"

    async def test_update_transaction_by_id(
        self, transaction_repo: TransactionRepository
    ):
        ts_utc = datetime.utcnow()
        data = TransactionCreate(
            amount=1000,
            payment_account_id=123,
            amount_paid=800,
            currency="USD",
            created_at=ts_utc,
            updated_at=ts_utc,
        )

        created = await transaction_repo.create_transaction(data)
        assert created.id, "transaction is created, assigned an ID"

        new_data = TransactionUpdate(
            amount=10000, payment_account_id=123, amount_paid=8000
        )

        updated_row = await transaction_repo.update_transaction_by_id(
            created.id, new_data
        )
        assert updated_row, "updated row"
        assert updated_row.id == created.id, "updated expected row"
        assert new_data.dict(
            include={"amount", "payment_account_id", "amount_paid"}
        ) == updated_row.dict(
            include={"amount", "payment_account_id", "amount_paid"}
        ), "updated content ok"

    async def test_set_transaction_payout_id_by_ids(
        self, transaction_repo: TransactionRepository
    ):
        ts_utc = datetime.utcnow()
        data = TransactionCreate(
            amount=1000,
            payment_account_id=123,
            amount_paid=800,
            currency="USD",
            created_at=ts_utc,
            updated_at=ts_utc,
        )

        first = await transaction_repo.create_transaction(data)
        second = await transaction_repo.create_transaction(data)
        assert first.id, "transaction is created, assigned an ID"
        assert second.id, "transaction is created, assigned an ID"

        transaction_ids = [first.id, second.id]
        new_data = TransactionUpdate(payout_id=101)

        updated_rows = await transaction_repo.set_transaction_payout_id_by_ids(
            transaction_ids, new_data
        )
        assert updated_rows, "updated"
        assert len(updated_rows) == 2, "both rows updated"
        for row in updated_rows:
            assert row.payout_id == new_data.payout_id, "payout id updated"
