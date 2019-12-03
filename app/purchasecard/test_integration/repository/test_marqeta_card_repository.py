from uuid import uuid4

import pytest

from app.purchasecard.models.maindb.marqeta_card import MarqetaCard


class TestMarqetaCardRepository:
    pytestmark = [pytest.mark.asyncio]
    TEST_TOKEN = "delight-1234"
    TEST_DELIGHT_NUMBER = 1234
    TEST_LAST4 = "6789"

    @pytest.fixture(autouse=True)
    def setup(self, marqeta_card_repo):
        self.marqeta_card_repo = marqeta_card_repo

    async def _create_card(self, token: str, delight_number: int, last4: str):
        card: MarqetaCard = await self.marqeta_card_repo.create(
            token=token, delight_number=delight_number, last4=last4
        )
        return card

    async def test_create_card_success(self):
        test_token = str(uuid4())
        card = await self._create_card(
            token=test_token,
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=self.TEST_LAST4,
        )

        assert card
        assert card.token == test_token
        assert card.delight_number == self.TEST_DELIGHT_NUMBER
        assert card.last4 == self.TEST_LAST4
        assert card.terminated_at is None

    async def test_get_card_success(self):
        test_token = str(uuid4())
        create_card: MarqetaCard = await self._create_card(
            token=test_token,
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=self.TEST_LAST4,
        )

        get_card: MarqetaCard = await self.marqeta_card_repo.get(
            token=test_token,
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=self.TEST_LAST4,
        )

        assert get_card
        assert get_card == create_card

    async def test_get_card_failure(self):
        test_token = str(uuid4())
        get_card: MarqetaCard = await self.marqeta_card_repo.get(
            token=test_token,
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=self.TEST_LAST4,
        )

        assert get_card is None
