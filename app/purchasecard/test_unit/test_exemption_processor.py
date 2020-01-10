import pytest
from asynctest import CoroutineMock

from app.purchasecard.core.exemption.processor import ExemptionProcessor


@pytest.mark.asyncio
class TestExemptionProcessor:
    @pytest.fixture
    def exemption_processor(
        self, mock_delivery_funding_repo, mock_marqeta_decline_exemption_repo
    ):
        return ExemptionProcessor(
            delivery_funding_repo=mock_delivery_funding_repo,
            decline_exemption_repo=mock_marqeta_decline_exemption_repo,
        )

    async def test_create_exemption(self, exemption_processor):
        exemption_processor.delivery_funding_repo.create = CoroutineMock()
        exemption_processor.decline_exemption_repo.create = CoroutineMock()
        await exemption_processor.create_exemption(
            creator_id="1", delivery_id="1", swipe_amount=100
        )
        exemption_processor.delivery_funding_repo.create.assert_awaited()
        exemption_processor.decline_exemption_repo.create.assert_not_awaited()

        exemption_processor.delivery_funding_repo.create.reset_mock()
        exemption_processor.decline_exemption_repo.create.reset_mock()

        await exemption_processor.create_exemption(
            creator_id="1",
            delivery_id="1",
            swipe_amount=100,
            dasher_id="123",
            decline_amount=100,
            mid="test_mid",
        )
        exemption_processor.decline_exemption_repo.create.assert_awaited()
        exemption_processor.delivery_funding_repo.create.assert_awaited()
