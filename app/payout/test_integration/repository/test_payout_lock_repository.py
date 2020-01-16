import uuid

import pytest
from app.payout.repository.paymentdb.model.payout_lock import PayoutLockCreate
from app.payout.repository.paymentdb.payout_lock import PayoutLockRepository


class TestPayoutLockRepository:
    pytestmark = [pytest.mark.asyncio]

    async def test_create_get_payout_lock(self, payout_lock_repo: PayoutLockRepository):
        # prepare and insert payout_lock, then validate
        suffix = str(uuid.uuid4())
        lock_id = f"test_payout_lock_{suffix}"
        data = PayoutLockCreate(lock_id=lock_id)

        payout_lock = await payout_lock_repo.create_payout_lock(data)
        assert payout_lock

        retrieved_payout_lock = await payout_lock_repo.get_payout_lock(lock_id)
        assert (
            payout_lock == retrieved_payout_lock
        ), "retrieved payout_lock should match"
