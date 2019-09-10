import pytest
from datetime import datetime

from app.commons.database.infra import DB
from app.payout.repository.bankdb.model.payout import PayoutUpdate
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.test_integration.utils import prepare_and_insert_payout


class TestPayoutRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payout_repo(self, payout_bankdb: DB) -> PayoutRepository:
        return PayoutRepository(database=payout_bankdb)

    async def test_create_get_payout(self, payout_repo: PayoutRepository):
        # prepare and insert payout, then validate
        payout = await prepare_and_insert_payout(payout_repo=payout_repo)
        assert payout == await payout_repo.get_payout_by_id(
            payout.id
        ), "retrieved payout matches"

    async def test_update_payout_by_id(self, payout_repo: PayoutRepository):
        # prepare and insert payout, then validate
        payout = await prepare_and_insert_payout(payout_repo=payout_repo)
        assert payout == await payout_repo.get_payout_by_id(
            payout.id
        ), "retrieved payout matches"

        timestamp = datetime.utcnow()
        new_data = PayoutUpdate(status="OK", updated_at=timestamp)
        updated = await payout_repo.update_payout_by_id(payout.id, new_data)
        assert updated, "updated"
        assert updated.status == "OK", "updated correctly"
        assert (
            updated.updated_at.timestamp() == timestamp.timestamp()
        ), "updated correctly"
