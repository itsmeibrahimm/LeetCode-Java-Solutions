from datetime import datetime
from typing import List
from uuid import uuid4

import pytest

from app.commons.database.infra import DB
from app.purchasecard.models.maindb.marqeta_card_ownership import MarqetaCardOwnership
from app.purchasecard.repository.marqeta_card_ownership import (
    MarqetaCardOwnershipRepository,
)


class TestMarqetaCardOwnershipRepository:
    pytestmark = [pytest.mark.asyncio]
    TEST_TOKEN = "delight-1234"
    TEST_DELIGHT_NUMBER = 1234
    TEST_LAST4 = "6789"
    TEST_DASHER_ID = 123456
    TEST_INVALID_DASHER_ID = 654321

    @pytest.fixture
    def marqeta_card_ownership_repo(
        self, purchasecard_maindb: DB
    ) -> MarqetaCardOwnershipRepository:
        return MarqetaCardOwnershipRepository(database=purchasecard_maindb)

    async def test_create_card_ownership(self, marqeta_card_ownership_repo):
        test_token = str(uuid4())
        ownership: MarqetaCardOwnership = await marqeta_card_ownership_repo.create_card_ownership(
            dasher_id=self.TEST_DASHER_ID, card_id=test_token
        )

        assert ownership
        assert ownership.dasher_id == self.TEST_DASHER_ID
        assert ownership.card_id == test_token
        assert ownership.created_at is not None

    async def test_get_card_ownership_by_id_success(self, marqeta_card_ownership_repo):
        test_token = str(uuid4())
        ownership: MarqetaCardOwnership = await marqeta_card_ownership_repo.create_card_ownership(
            dasher_id=self.TEST_DASHER_ID, card_id=test_token
        )

        get_ownership: MarqetaCardOwnership = await marqeta_card_ownership_repo.get_card_ownership_by_id(
            marqeta_card_ownership_id=ownership.id
        )

        assert get_ownership
        assert get_ownership == ownership

    async def test_get_card_ownership_by_id_failure(self, marqeta_card_ownership_repo):
        # create a new table entry, its id+1 will guarantee the following `get` fails
        test_token = str(uuid4())
        ownership: MarqetaCardOwnership = await marqeta_card_ownership_repo.create_card_ownership(
            dasher_id=self.TEST_DASHER_ID, card_id=test_token
        )
        test_id = ownership.id + 1
        get_ownership: MarqetaCardOwnership = await marqeta_card_ownership_repo.get_card_ownership_by_id(
            marqeta_card_ownership_id=test_id
        )

        assert not get_ownership

    async def test_get_active_card_ownerships_by_card_id_success(
        self, marqeta_card_ownership_repo
    ):
        test_token = str(uuid4())
        ownership_one = await marqeta_card_ownership_repo.create_card_ownership(
            dasher_id=self.TEST_DASHER_ID, card_id=test_token
        )
        ownership_two = await marqeta_card_ownership_repo.create_card_ownership(
            dasher_id=self.TEST_DASHER_ID, card_id=test_token
        )
        ownerships: List[
            MarqetaCardOwnership
        ] = await marqeta_card_ownership_repo.get_active_card_ownerships_by_card_id(
            card_id=test_token
        )

        assert len(ownerships) == 2
        assert ownership_one in ownerships
        assert ownership_two in ownerships

    async def test_get_active_card_ownerships_by_card_id_failure(
        self, marqeta_card_ownership_repo
    ):
        test_token = str(uuid4())
        ownerships: List[
            MarqetaCardOwnership
        ] = await marqeta_card_ownership_repo.get_active_card_ownerships_by_card_id(
            card_id=test_token
        )
        assert ownerships == []

    async def test_get_active_card_ownership_by_dasher_id_success(
        self, marqeta_card_ownership_repo
    ):
        test_token = str(uuid4())
        active_ownership: MarqetaCardOwnership = await marqeta_card_ownership_repo.create_card_ownership(
            dasher_id=self.TEST_DASHER_ID, card_id=test_token
        )

        ownership: MarqetaCardOwnership = await marqeta_card_ownership_repo.get_active_card_ownership_by_dasher_id(
            dasher_id=self.TEST_DASHER_ID
        )

        assert ownership
        assert ownership == active_ownership
        assert ownership.ended_at is None

    async def test_get_active_card_ownership_by_dasher_id_failure(
        self, marqeta_card_ownership_repo
    ):
        ownership: MarqetaCardOwnership = await marqeta_card_ownership_repo.get_active_card_ownership_by_dasher_id(
            dasher_id=self.TEST_INVALID_DASHER_ID
        )

        assert not ownership

    async def test_update_ownership_ended_at_success(self, marqeta_card_ownership_repo):
        test_token = str(uuid4())
        active_ownership: MarqetaCardOwnership = await marqeta_card_ownership_repo.create_card_ownership(
            dasher_id=self.TEST_DASHER_ID, card_id=test_token
        )
        assert active_ownership

        ended_ownership: MarqetaCardOwnership = await marqeta_card_ownership_repo.update_card_ownership_ended_at(
            marqeta_card_ownership_id=active_ownership.id, ended_at=datetime.utcnow()
        )

        assert ended_ownership
        assert ended_ownership.id == active_ownership.id
        assert ended_ownership.ended_at is not None

    async def test_update_ownership_ended_at_failure(self, marqeta_card_ownership_repo):
        # create a new table entry, its id+1 will guarantee a non-existing id in table
        test_token = str(uuid4())
        ownership: MarqetaCardOwnership = await marqeta_card_ownership_repo.create_card_ownership(
            dasher_id=self.TEST_DASHER_ID, card_id=test_token
        )
        test_id = ownership.id + 1
        ended_ownership: MarqetaCardOwnership = await marqeta_card_ownership_repo.update_card_ownership_ended_at(
            marqeta_card_ownership_id=test_id, ended_at=datetime.utcnow()
        )

        assert ended_ownership is None
