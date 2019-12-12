import pytest
from datetime import datetime, timedelta
from app.purchasecard.test_integration.utils import (
    prepare_and_insert_marqeta_transaction_data,
)


class TestMarqetaTransactionRepository:
    pytestmark = [pytest.mark.asyncio]

    TEST_AMOUNT1 = 1
    TEST_AMOUNT2 = 2
    TEST_AMOUNT3 = 3

    @pytest.fixture(autouse=True)
    def setup(self, marqeta_transaction_repo):
        self.marqeta_transaction_repo = marqeta_transaction_repo

    async def test_get_funded_amount_by_delivery_id(self):
        await prepare_and_insert_marqeta_transaction_data(
            marqeta_tx_repo=self.marqeta_transaction_repo,
            id=1,
            token="token1",
            amount=self.TEST_AMOUNT1,
            delivery_id=1,
            card_acceptor="1",
            timed_out=False,
            swiped_at=None,
        )
        await prepare_and_insert_marqeta_transaction_data(
            marqeta_tx_repo=self.marqeta_transaction_repo,
            id=2,
            token="token2",
            amount=self.TEST_AMOUNT2,
            delivery_id=1,
            card_acceptor="1",
            timed_out=False,
            swiped_at=None,
        )
        result = await self.marqeta_transaction_repo.get_funded_amount_by_delivery_id(1)
        assert result == self.TEST_AMOUNT1 + self.TEST_AMOUNT2

        await prepare_and_insert_marqeta_transaction_data(
            marqeta_tx_repo=self.marqeta_transaction_repo,
            id=3,
            token="token3",
            amount=self.TEST_AMOUNT3,
            delivery_id=3,
            card_acceptor="1",
            timed_out=None,
            swiped_at=(datetime.now() - timedelta(seconds=60)),
        )
        result = await self.marqeta_transaction_repo.get_funded_amount_by_delivery_id(3)
        assert result == self.TEST_AMOUNT3
