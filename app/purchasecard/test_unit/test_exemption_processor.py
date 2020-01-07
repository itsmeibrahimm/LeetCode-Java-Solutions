import pytest
from asynctest import patch, asynctest, MagicMock

from app.purchasecard.core.exemption.processor import ExemptionProcessor


@pytest.mark.asyncio
class TestExemptionProcessor:
    @pytest.fixture
    def exemption_processor(
        self, delivery_funding_repo, marqeta_decline_exemption_repo
    ):
        return ExemptionProcessor(
            delivery_funding_repo=delivery_funding_repo,
            decline_exemption_repo=marqeta_decline_exemption_repo,
        )

    @patch(
        "app.purchasecard.repository.delivery_funding.DeliveryFundingRepository.create",
        scope=asynctest.LIMITED,
    )
    @patch(
        "app.purchasecard.repository.marqeta_decline_exemption.MarqetaDeclineExemptionRepository.create",
        scope=asynctest.LIMITED,
    )
    async def test_create_exemption(
        self,
        mock_create_decline_exemption,
        mock_create_delivery_funding,
        exemption_processor,
    ):
        mock_create_delivery_funding.return_value = MagicMock()
        await exemption_processor.create_exemption(
            creator_id="1", delivery_id="1", swipe_amount=100
        )
        mock_create_delivery_funding.assert_awaited()
        mock_create_decline_exemption.assert_not_awaited()

        mock_create_delivery_funding.reset_mock()
        mock_create_decline_exemption.reset_mock()

        mock_create_delivery_funding.return_value = MagicMock()
        mock_create_decline_exemption.return_value = MagicMock()
        await exemption_processor.create_exemption(
            creator_id="1",
            delivery_id="1",
            swipe_amount=100,
            dasher_id="123",
            decline_amount=100,
            mid="test_mid",
        )
        mock_create_delivery_funding.assert_awaited()
        mock_create_decline_exemption.assert_awaited()
