import pytest
from asynctest import MagicMock, CoroutineMock

from app.purchasecard.core.transaction.processor import TransactionProcessor
from app.purchasecard.constants import BUFFER_MULTIPLIER_FOR_DELIVERY


@pytest.mark.asyncio
class TestTransactionProcessor:
    TEST_DELIVERY_ID = "123"
    TEST_FUNDED_AMOUNT = 100
    TEST_TOTAL_FUNDING = 20
    TEST_RESTAURANT_TOTAL = 200

    @pytest.fixture(autouse=True)
    def setup(self, mock_marqeta_transaction_repo, mock_delivery_funding_repo):
        self.transaction_processor = TransactionProcessor(
            logger=MagicMock(),
            marqeta_repository=mock_marqeta_transaction_repo,
            delivery_funding_repository=mock_delivery_funding_repo,
        )

    async def test_get_fundable_amount_by_delivery_id(self):
        self.transaction_processor.marqeta_repository.get_funded_amount_by_delivery_id = CoroutineMock(
            return_value=100
        )
        self.transaction_processor.delivery_funding_repository.get_total_funding_by_delivery_id = CoroutineMock(
            return_value=20
        )
        result = await self.transaction_processor.get_fundable_amount_by_delivery_id(
            delivery_id=self.TEST_DELIVERY_ID,
            restaurant_total=self.TEST_RESTAURANT_TOTAL,
        )
        assert (
            result
            == BUFFER_MULTIPLIER_FOR_DELIVERY * self.TEST_RESTAURANT_TOTAL
            + self.TEST_TOTAL_FUNDING
            - self.TEST_FUNDED_AMOUNT
        )

    async def test_has_associated_marqeta_transaction(self):
        self.transaction_processor.marqeta_repository.has_associated_marqeta_transaction = CoroutineMock(
            return_value=False
        )
        assert not await self.transaction_processor.has_associated_marqeta_transaction(
            delivery_id=self.TEST_DELIVERY_ID, ignore_timed_out=True
        )
        assert not await self.transaction_processor.has_associated_marqeta_transaction(
            delivery_id=self.TEST_DELIVERY_ID, ignore_timed_out=False
        )
        self.transaction_processor.marqeta_repository.has_associated_marqeta_transaction = CoroutineMock(
            return_value=True
        )
        assert await self.transaction_processor.has_associated_marqeta_transaction(
            delivery_id=self.TEST_DELIVERY_ID, ignore_timed_out=True
        )
        assert await self.transaction_processor.has_associated_marqeta_transaction(
            delivery_id=self.TEST_DELIVERY_ID, ignore_timed_out=False
        )
