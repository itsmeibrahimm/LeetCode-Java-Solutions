import random
from uuid import uuid4

import pytest
from datetime import datetime, timedelta, timezone

from app.commons.database.infra import DB
from app.purchasecard.repository.marqeta_transaction import MarqetaTransactionRepository
from app.purchasecard.test_integration.utils import (
    prepare_and_insert_marqeta_transaction_data,
)


@pytest.mark.asyncio
class TestMarqetaTransactionRepository:
    TEST_AMOUNT1 = 1
    TEST_AMOUNT2 = 2
    TEST_AMOUNT3 = 3

    @pytest.fixture
    def marqeta_transaction_repo(
        self, purchasecard_maindb: DB
    ) -> MarqetaTransactionRepository:
        return MarqetaTransactionRepository(database=purchasecard_maindb)

    async def test_get_funded_amount_by_delivery_id(self, marqeta_transaction_repo):
        delivery_id_1 = random.randint(100000, 5000000)
        mock_txn_1 = await prepare_and_insert_marqeta_transaction_data(
            marqeta_tx_repo=marqeta_transaction_repo,
            token=str(uuid4()),
            amount=self.TEST_AMOUNT1,
            delivery_id=delivery_id_1,
            card_acceptor="1",
            timed_out=False,
            swiped_at=None,
        )
        assert mock_txn_1.amount == 1
        mock_txn_2 = await prepare_and_insert_marqeta_transaction_data(
            marqeta_tx_repo=marqeta_transaction_repo,
            token=str(uuid4()),
            amount=self.TEST_AMOUNT2,
            delivery_id=delivery_id_1,
            card_acceptor="1",
            timed_out=False,
            swiped_at=None,
        )
        assert mock_txn_2.amount == 2
        result = await marqeta_transaction_repo.get_funded_amount_by_delivery_id(
            delivery_id_1
        )
        assert result == self.TEST_AMOUNT1 + self.TEST_AMOUNT2

        delivery_id_2 = random.randint(100000, 5000000)
        await prepare_and_insert_marqeta_transaction_data(
            marqeta_tx_repo=marqeta_transaction_repo,
            token=str(uuid4()),
            amount=self.TEST_AMOUNT3,
            delivery_id=delivery_id_2,
            card_acceptor="1",
            timed_out=None,
            swiped_at=(datetime.now(timezone.utc) - timedelta(seconds=20)),
        )
        result = await marqeta_transaction_repo.get_funded_amount_by_delivery_id(
            delivery_id_2
        )
        assert result == self.TEST_AMOUNT3

        delivery_id_3 = random.randint(100000, 5000000)
        await prepare_and_insert_marqeta_transaction_data(
            marqeta_tx_repo=marqeta_transaction_repo,
            token=str(uuid4()),
            amount=self.TEST_AMOUNT3,
            delivery_id=delivery_id_3,
            card_acceptor="3",
            timed_out=None,
            swiped_at=(datetime.now(timezone.utc) - timedelta(seconds=60)),
        )
        result = await marqeta_transaction_repo.get_funded_amount_by_delivery_id(
            delivery_id_3
        )
        assert result == 0

    async def test_no_marqeta_transaction_associated_with_delivery(
        self, marqeta_transaction_repo
    ):
        delivery_id = random.randint(100000, 5000000)
        result = await marqeta_transaction_repo.has_associated_marqeta_transaction(
            delivery_id=delivery_id, ignore_timed_out=True
        )
        assert not result
        result = await marqeta_transaction_repo.has_associated_marqeta_transaction(
            delivery_id=delivery_id, ignore_timed_out=False
        )
        assert not result

    async def test_marqeta_transaction_associated_with_delivery(
        self, marqeta_transaction_repo
    ):
        delivery_id = random.randint(100000, 5000000)
        await prepare_and_insert_marqeta_transaction_data(
            marqeta_tx_repo=marqeta_transaction_repo,
            token=str(uuid4()),
            amount=self.TEST_AMOUNT1,
            delivery_id=delivery_id,
            card_acceptor="1",
            timed_out=None,
            swiped_at=None,
        )
        result = await marqeta_transaction_repo.has_associated_marqeta_transaction(
            delivery_id=delivery_id, ignore_timed_out=True
        )
        assert result
        result = await marqeta_transaction_repo.has_associated_marqeta_transaction(
            delivery_id=delivery_id, ignore_timed_out=False
        )
        assert not result
        await prepare_and_insert_marqeta_transaction_data(
            marqeta_tx_repo=marqeta_transaction_repo,
            token=str(uuid4()),
            amount=self.TEST_AMOUNT1,
            delivery_id=delivery_id,
            card_acceptor="1",
            timed_out=False,
            swiped_at=None,
        )
        result = await marqeta_transaction_repo.has_associated_marqeta_transaction(
            delivery_id=delivery_id, ignore_timed_out=False
        )
        assert result

    async def test_get_last_transaction_by_delivery_id(self, marqeta_transaction_repo):
        delivery_id = random.randint(100000, 5000000)
        await prepare_and_insert_marqeta_transaction_data(
            marqeta_tx_repo=marqeta_transaction_repo,
            token=str(uuid4()),
            amount=self.TEST_AMOUNT1,
            delivery_id=delivery_id,
            card_acceptor="1",
            timed_out=None,
            swiped_at=None,
        )
        latest_transaction = await prepare_and_insert_marqeta_transaction_data(
            marqeta_tx_repo=marqeta_transaction_repo,
            token=str(uuid4()),
            amount=self.TEST_AMOUNT2,
            delivery_id=delivery_id,
            card_acceptor="1",
            timed_out=None,
            swiped_at=None,
        )
        result = await marqeta_transaction_repo.get_last_transaction_by_delivery_id(
            delivery_id=delivery_id
        )
        assert result
        assert result.id == latest_transaction.id

        wrong_delivery_id = random.randint(5000000, 9000000)
        none_result = await marqeta_transaction_repo.get_last_transaction_by_delivery_id(
            delivery_id=wrong_delivery_id
        )
        assert none_result is None
