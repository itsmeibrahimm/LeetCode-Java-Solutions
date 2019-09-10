import pytest
from datetime import datetime, timezone

from app.commons.database.infra import DB
from app.payout.repository.bankdb.model.transaction import TransactionUpdate
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.test_integration.utils import prepare_and_insert_transaction


class TestTransactionRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def transaction_repo(self, payout_bankdb: DB) -> TransactionRepository:
        return TransactionRepository(database=payout_bankdb)

    async def test_create_get_transaction(
        self, transaction_repo: TransactionRepository
    ):
        transaction = await prepare_and_insert_transaction(
            transaction_repo=transaction_repo
        )
        assert transaction == await transaction_repo.get_transaction_by_id(
            transaction.id
        ), "retrieved transaction matches"

    async def test_update_transaction_by_id(
        self, transaction_repo: TransactionRepository
    ):
        transaction = await prepare_and_insert_transaction(
            transaction_repo=transaction_repo
        )
        new_data = TransactionUpdate(
            amount=10000, payment_account_id=123, amount_paid=8000
        )

        updated_row = await transaction_repo.update_transaction_by_id(
            transaction.id, new_data
        )
        assert updated_row, "updated row"
        assert updated_row.id == transaction.id, "updated expected row"
        assert new_data.dict(
            include={"amount", "payment_account_id", "amount_paid"}
        ) == updated_row.dict(
            include={"amount", "payment_account_id", "amount_paid"}
        ), "updated content ok"

    async def test_set_transaction_payout_id_by_ids(
        self, transaction_repo: TransactionRepository
    ):
        timestamp = datetime.now(timezone.utc)
        first_txn = await prepare_and_insert_transaction(
            transaction_repo=transaction_repo, timestamp=timestamp
        )
        second_txn = await prepare_and_insert_transaction(
            transaction_repo=transaction_repo, timestamp=timestamp
        )

        transaction_ids = [first_txn.id, second_txn.id]
        new_data = TransactionUpdate(payout_id=101)

        updated_rows = await transaction_repo.set_transaction_payout_id_by_ids(
            transaction_ids, new_data
        )
        assert updated_rows, "updated"
        assert len(updated_rows) == 2, "both rows updated"
        for row in updated_rows:
            assert row.payout_id == new_data.payout_id, "payout id updated"
