import pytest

from app.commons.database.infra import DB
from app.purchasecard.repository.delivery_funding import DeliveryFundingRepository
from app.purchasecard.test_integration.utils import (
    prepare_and_insert_delivery_funding_data,
)


@pytest.mark.asyncio
class TestDeliveryFundingRepository:
    @pytest.fixture
    def delivery_funding_repo(
        self, purchasecard_maindb: DB
    ) -> DeliveryFundingRepository:
        return DeliveryFundingRepository(database=purchasecard_maindb)

    async def test_create(self, delivery_funding_repo: DeliveryFundingRepository):
        await prepare_and_insert_delivery_funding_data(
            delivery_funding_repo=delivery_funding_repo,
            creator_id=1,
            delivery_id=123,
            swipe_amount=100,
        )
