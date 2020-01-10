import pytest

from app.commons.database.infra import DB
from app.purchasecard.repository.marqeta_decline_exemption import (
    MarqetaDeclineExemptionRepository,
)
from app.purchasecard.test_integration.utils import (
    prepare_and_insert_marqeta_decline_exemption,
)


@pytest.mark.asyncio
class TestMarqetaDeclineExemptionRepository:
    @pytest.fixture
    def marqeta_decline_exemption_repo(
        self, purchasecard_maindb: DB
    ) -> MarqetaDeclineExemptionRepository:
        return MarqetaDeclineExemptionRepository(database=purchasecard_maindb)

    async def test_create(
        self, marqeta_decline_exemption_repo: MarqetaDeclineExemptionRepository
    ):
        await prepare_and_insert_marqeta_decline_exemption(
            marqeta_decline_exemption_repo=marqeta_decline_exemption_repo,
            creator_id=1,
            delivery_id=123,
            amount=100,
            dasher_id=12,
            mid="test_mid",
        )
