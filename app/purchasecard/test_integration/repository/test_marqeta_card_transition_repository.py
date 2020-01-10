from datetime import datetime
from typing import List
from uuid import uuid4

import pytest

from app.commons.database.infra import DB
from app.purchasecard.models.maindb.marqeta_card import MarqetaCard
from app.purchasecard.models.maindb.marqeta_card_transition import (
    MarqetaCardTransition,
    TransitionState,
)
from app.purchasecard.repository.marqeta_card import MarqetaCardRepository
from app.purchasecard.repository.marqeta_card_transition import (
    MarqetaCardTransitionRepository,
)


class TestMarqetaCardTransitionRepository:
    pytestmark = [pytest.mark.asyncio]
    TEST_TOKEN = "delight-1234"
    TEST_DELIGHT_NUMBER = 1234
    TEST_LAST4 = "6789"
    TEST_DASHER_ID = 123456
    TEST_INVALID_DASHER_ID = 654321

    @pytest.fixture
    def marqeta_card_repo(self, purchasecard_maindb: DB) -> MarqetaCardRepository:
        return MarqetaCardRepository(database=purchasecard_maindb)

    @pytest.fixture
    def marqeta_card_transition_repo(
        self, purchasecard_maindb: DB
    ) -> MarqetaCardTransitionRepository:
        return MarqetaCardTransitionRepository(database=purchasecard_maindb)

    async def test_create_transition(
        self, marqeta_card_transition_repo, marqeta_card_repo
    ):
        test_token = str(uuid4())
        card: MarqetaCard = await marqeta_card_repo.create(
            token=test_token,
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=self.TEST_LAST4,
        )
        assert card
        transition: MarqetaCardTransition = await marqeta_card_transition_repo.create_transition(
            card_id=test_token, desired_state=TransitionState.ACTIVE
        )

        assert transition
        assert transition.card_id == test_token
        assert transition.desired_state == TransitionState.ACTIVE
        assert transition.created_at is not None

    async def test_get_failed_transitions_success(
        self, marqeta_card_transition_repo, marqeta_card_repo
    ):
        test_token = str(uuid4())
        card: MarqetaCard = await marqeta_card_repo.create(
            token=test_token,
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=self.TEST_LAST4,
        )
        assert card

        new_transition_one: MarqetaCardTransition = await marqeta_card_transition_repo.create_transition(
            card_id=test_token, desired_state=TransitionState.ACTIVE
        )
        assert new_transition_one

        new_transition_two: MarqetaCardTransition = await marqeta_card_transition_repo.create_transition(
            card_id=test_token, desired_state=TransitionState.INACTIVE
        )
        assert new_transition_two

        failed_transitions: List[
            MarqetaCardTransition
        ] = await marqeta_card_transition_repo.get_failed_transitions(
            card_id=test_token
        )

        assert failed_transitions
        assert new_transition_one in failed_transitions
        assert new_transition_two in failed_transitions

    async def test_get_failed_transitions_failure(
        self, marqeta_card_transition_repo, marqeta_card_repo
    ):
        test_token = str(uuid4())
        transitions: List[
            MarqetaCardTransition
        ] = await marqeta_card_transition_repo.get_failed_transitions(
            card_id=test_token
        )

        assert transitions == []

    async def test_update_transition_aborted_at_success(
        self, marqeta_card_transition_repo, marqeta_card_repo
    ):
        test_token = str(uuid4())
        card: MarqetaCard = await marqeta_card_repo.create(
            token=test_token,
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=self.TEST_LAST4,
        )
        assert card

        transition: MarqetaCardTransition = await marqeta_card_transition_repo.create_transition(
            card_id=test_token, desired_state=TransitionState.ACTIVE
        )
        assert transition

        updated_transitions: List[
            MarqetaCardTransition
        ] = await marqeta_card_transition_repo.update_transitions_aborted_at(
            transition_ids=[transition.id], aborted_at=datetime.utcnow()
        )

        assert updated_transitions
        assert updated_transitions[0].id == transition.id
        assert updated_transitions[0].aborted_at is not None

    async def test_update_transition_aborted_at_failure(
        self, marqeta_card_transition_repo, marqeta_card_repo
    ):
        test_token = str(uuid4())
        card: MarqetaCard = await marqeta_card_repo.create(
            token=test_token,
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=self.TEST_LAST4,
        )
        assert card

        transition: MarqetaCardTransition = await marqeta_card_transition_repo.create_transition(
            card_id=test_token, desired_state=TransitionState.ACTIVE
        )
        assert transition

        updated_transitions: List[
            MarqetaCardTransition
        ] = await marqeta_card_transition_repo.update_transitions_aborted_at(
            transition_ids=[transition.id + 1], aborted_at=datetime.utcnow()
        )

        assert updated_transitions == []

    async def test_update_transition_succeeded_at_success(
        self, marqeta_card_transition_repo, marqeta_card_repo
    ):
        test_token = str(uuid4())
        card: MarqetaCard = await marqeta_card_repo.create(
            token=test_token,
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=self.TEST_LAST4,
        )
        assert card

        transition: MarqetaCardTransition = await marqeta_card_transition_repo.create_transition(
            card_id=test_token, desired_state=TransitionState.ACTIVE
        )
        assert transition

        updated_transitions: List[
            MarqetaCardTransition
        ] = await marqeta_card_transition_repo.update_transitions_succeeded_at(
            transition_ids=[transition.id], succeeded_at=datetime.utcnow()
        )

        assert updated_transitions
        assert updated_transitions[0].id == transition.id
        assert updated_transitions[0].succeeded_at is not None

    async def test_update_transition_succeeded_at_failure(
        self, marqeta_card_transition_repo, marqeta_card_repo
    ):
        test_token = str(uuid4())
        card: MarqetaCard = await marqeta_card_repo.create(
            token=test_token,
            delight_number=self.TEST_DELIGHT_NUMBER,
            last4=self.TEST_LAST4,
        )
        assert card

        transition: MarqetaCardTransition = await marqeta_card_transition_repo.create_transition(
            card_id=test_token, desired_state=TransitionState.ACTIVE
        )
        assert transition

        updated_transitions: List[
            MarqetaCardTransition
        ] = await marqeta_card_transition_repo.update_transitions_succeeded_at(
            transition_ids=[transition.id + 1], succeeded_at=datetime.utcnow()
        )

        assert updated_transitions == []
