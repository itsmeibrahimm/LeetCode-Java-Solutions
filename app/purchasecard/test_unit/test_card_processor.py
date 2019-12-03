from datetime import datetime, timedelta

import pytest
from asynctest import MagicMock, CoroutineMock

from app.purchasecard.core.card.models import InternalAssociateCardResponse
from app.purchasecard.core.card.processor import CardProcessor
from app.purchasecard.marqeta_external.models import (
    MarqetaProviderCard,
    FulfillmentStatus,
    CardState,
)
from app.purchasecard.models.maindb.marqeta_card import MarqetaCard
from app.purchasecard.models.maindb.marqeta_card_ownership import MarqetaCardOwnership
from app.purchasecard.models.maindb.marqeta_card_transition import (
    MarqetaCardTransition,
    TransitionState,
)


class FunctionMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(FunctionMock, self).__call__(*args, **kwargs)


class TestCardProcessor:
    pytestmark = [pytest.mark.asyncio]
    TEST_TOKEN: str = "card_processor_test_token"
    TEST_DELIGHT_NUMBER: int = 1234
    TEST_LAST_FOUR: str = "1234"
    TEST_DASHER_ID: int = 1234
    TEST_USER_TOKEN: int = 1234

    @pytest.fixture(autouse=True)
    def setup(
        self,
        fake_marqeta_client,
        mock_marqeta_card_repo,
        mock_marqeta_card_ownership_repo,
        mock_marqeta_card_transition_repo,
    ):
        self.card_processor = CardProcessor(
            logger=MagicMock(),
            marqeta_client=fake_marqeta_client,
            card_repo=mock_marqeta_card_repo,
            card_ownership_repo=mock_marqeta_card_ownership_repo,
            card_transition_repo=mock_marqeta_card_transition_repo,
        )

    def get_fake_marqeta_card(self, token, last_four):
        return MarqetaProviderCard(
            created_time=datetime.utcnow(),
            last_modified_time=datetime.utcnow(),
            token=token,
            user_token="",
            last_four=last_four,
            card_product_token="",
            pan="",
            expiration="",
            expiration_time=datetime.utcnow() + timedelta(days=365),
            barcode="",
            pin_is_set=True,
            state=CardState.UNACTIVATED,
            state_reason="",
            fulfillment_status=FulfillmentStatus.ISSUED,
            instrument_type="",
            expedite=False,
        )

    @pytest.fixture
    def fake_marqeta_client(self):
        mock_marqeta_client = MagicMock()
        mock_marqeta_client.get_marqeta_card_and_verify = FunctionMock()
        mock_marqeta_client.get_marqeta_card_and_verify.return_value = self.get_fake_marqeta_card(
            token=self.TEST_TOKEN, last_four=self.TEST_LAST_FOUR
        )
        mock_marqeta_client.get_card_token_prefix_cutover_id = MagicMock()
        mock_marqeta_client.get_card_token_prefix_cutover_id.return_value = 73617

        mock_marqeta_client.update_card_activation = FunctionMock()
        mock_marqeta_client.update_card_activation.return_value = None

        mock_marqeta_client.update_card_user_token = FunctionMock()
        mock_marqeta_client.update_card_user_token.return_value = None
        return mock_marqeta_client

    async def test_assign_card_to_dasher_one_prev_owner(self):
        """
        mock DB calls
        """
        self.card_processor.get_or_create = CoroutineMock()
        self.card_processor.get_or_create.return_value = (
            MarqetaCard(
                token=self.TEST_TOKEN,
                delight_number=self.TEST_DELIGHT_NUMBER,
                last4=self.TEST_LAST_FOUR,
            ),
            False,
        )

        self.card_processor.card_ownership_repo.get_active_card_ownerships_by_card_id = (
            CoroutineMock()
        )
        self.card_processor.card_ownership_repo.get_active_card_ownerships_by_card_id.return_value = [
            MarqetaCardOwnership(
                id=0,
                created_at=datetime.utcnow(),
                card_id=self.TEST_TOKEN,
                dasher_id=self.TEST_DASHER_ID,
            )
        ]

        self.card_processor.card_ownership_repo.update_card_ownership_ended_at = (
            CoroutineMock()
        )
        self.card_processor.card_ownership_repo.update_card_ownership_ended_at.return_value = (
            None
        )

        self.card_processor.card_ownership_repo.get_active_card_ownership_by_dasher_id = (
            CoroutineMock()
        )
        self.card_processor.card_ownership_repo.get_active_card_ownership_by_dasher_id.return_value = MarqetaCardOwnership(
            id=1,
            created_at=datetime.utcnow(),
            card_id=self.TEST_TOKEN,
            dasher_id=self.TEST_DASHER_ID,
        )

        self.card_processor.card_transition_repo.get_failed_transitions = (
            CoroutineMock()
        )
        self.card_processor.card_transition_repo.get_failed_transitions.return_value = [
            MarqetaCardTransition(
                id=0,
                created_at=datetime.utcnow(),
                desired_state=TransitionState.ACTIVE,
                card_id=self.TEST_TOKEN,
            )
        ]
        self.card_processor.card_transition_repo.update_transitions_aborted_at = (
            CoroutineMock()
        )
        self.card_processor.card_transition_repo.update_transitions_aborted_at.return_value = (
            None
        )

        self.card_processor.card_transition_repo.create_transition = CoroutineMock()
        self.card_processor.card_transition_repo.create_transition.return_value = MarqetaCardTransition(
            id=1,
            created_at=datetime.utcnow(),
            desired_state=TransitionState.INACTIVE,
            card_id=self.TEST_TOKEN,
        )

        self.card_processor.card_ownership_repo.create_card_ownership = CoroutineMock()
        self.card_processor.card_ownership_repo.create_card_ownership.return_value = (
            None
        )

        #  Test give card to dasher
        response: InternalAssociateCardResponse = await self.card_processor.associate_card_with_dasher(
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=self.TEST_LAST_FOUR,
            is_dispatcher=True,
            dasher_id=self.TEST_DASHER_ID,
            user_token=self.TEST_USER_TOKEN,
        )

        assert response
        assert response.old_card_relinquished is True
        assert response.num_prev_owners == 1

    async def test_assign_card_to_dasher_no_prev_owners(self):
        """
        mock DB calls
        """
        self.card_processor.get_or_create = CoroutineMock()
        self.card_processor.get_or_create.return_value = (
            MarqetaCard(
                token=self.TEST_TOKEN,
                delight_number=self.TEST_DELIGHT_NUMBER,
                last4=self.TEST_LAST_FOUR,
            ),
            False,
        )

        self.card_processor.card_ownership_repo.get_active_card_ownerships_by_card_id = (
            CoroutineMock()
        )
        self.card_processor.card_ownership_repo.get_active_card_ownerships_by_card_id.return_value = (
            []
        )

        self.card_processor.card_ownership_repo.update_card_ownership_ended_at = (
            CoroutineMock()
        )
        self.card_processor.card_ownership_repo.update_card_ownership_ended_at.return_value = (
            None
        )

        self.card_processor.card_ownership_repo.get_active_card_ownership_by_dasher_id = (
            CoroutineMock()
        )
        self.card_processor.card_ownership_repo.get_active_card_ownership_by_dasher_id.return_value = MarqetaCardOwnership(
            id=1,
            created_at=datetime.utcnow(),
            card_id=self.TEST_TOKEN,
            dasher_id=self.TEST_DASHER_ID,
        )

        self.card_processor.card_transition_repo.get_failed_transitions = (
            CoroutineMock()
        )
        self.card_processor.card_transition_repo.get_failed_transitions.return_value = [
            MarqetaCardTransition(
                id=0,
                created_at=datetime.utcnow(),
                desired_state=TransitionState.ACTIVE,
                card_id=self.TEST_TOKEN,
            )
        ]
        self.card_processor.card_transition_repo.update_transitions_aborted_at = (
            CoroutineMock()
        )
        self.card_processor.card_transition_repo.update_transitions_aborted_at.return_value = (
            None
        )

        self.card_processor.card_transition_repo.create_transition = CoroutineMock()
        self.card_processor.card_transition_repo.create_transition.return_value = MarqetaCardTransition(
            id=1,
            created_at=datetime.utcnow(),
            desired_state=TransitionState.INACTIVE,
            card_id=self.TEST_TOKEN,
        )

        self.card_processor.card_ownership_repo.create_card_ownership = CoroutineMock()
        self.card_processor.card_ownership_repo.create_card_ownership.return_value = (
            None
        )

        #  Test give card to dasher
        response: InternalAssociateCardResponse = await self.card_processor.associate_card_with_dasher(
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=self.TEST_LAST_FOUR,
            is_dispatcher=True,
            dasher_id=self.TEST_DASHER_ID,
            user_token=self.TEST_USER_TOKEN,
        )

        assert response
        assert response.old_card_relinquished is True
        assert response.num_prev_owners == 0
