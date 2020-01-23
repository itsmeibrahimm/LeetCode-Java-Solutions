import asyncio
import uuid

import pytest

from app.commons.core.errors import (
    PaymentDBLockAcquireError,
    PaymentDBLockErrorCode,
    payment_db_lock_error_message_maps,
    PaymentDBLockReleaseError,
)
from app.commons.lock.lockable import Lockable
from app.commons.lock.payment_db_lock import PaymentDBLock
from app.payout.repository.paymentdb.payout_lock import PayoutLockRepository


class TestPayoutLock:
    pytestmark = [pytest.mark.asyncio]

    def setup(self):
        self.lock_id = "payout_account_lock" + str(uuid.uuid4())
        self.counter = 1

    async def test_successfully_acquire_lock(
        self, payout_lock_repo: PayoutLockRepository
    ):
        async with PaymentDBLock(payout_lock_repo, self.lock_id) as lock:
            assert await lock.is_locked() is True
            await asyncio.sleep(1)
            assert await lock.is_locked() is True
        assert await lock.is_locked() is False

    async def test_acquire_same_lock_when_first_lock_is_released(
        self, payout_lock_repo: PayoutLockRepository
    ):
        lock_id = self.lock_id
        async with PaymentDBLock(payout_lock_repo, lock_id) as lock1:
            assert await lock1.is_locked() is True
        assert await lock1.is_locked() is False

        # Should successfully acquire same lock when first one is released
        async with PaymentDBLock(payout_lock_repo, lock_id) as lock2:
            assert await lock2.is_locked() is True
        assert await lock2.is_locked() is False

    async def test_acquire_same_lock_when_first_lock_is_not_released(
        self, payout_lock_repo: PayoutLockRepository
    ):
        lock_id = self.lock_id
        async with PaymentDBLock(payout_lock_repo, lock_id) as lock1:
            assert await lock1.is_locked() is True
            # Should raise PaymentDBLockAcquireError when lock1 is not released
            with pytest.raises(PaymentDBLockAcquireError):
                async with PaymentDBLock(payout_lock_repo, lock_id):
                    pass
        assert await lock1.is_locked() is False

    async def test_acquire_same_lock_when_first_lock_is_held_too_long(
        self, payout_lock_repo: PayoutLockRepository
    ):
        lock_id = self.lock_id
        with pytest.raises(PaymentDBLockReleaseError):
            async with PaymentDBLock(payout_lock_repo, lock_id, ttl_sec=1) as lock1:
                assert await lock1.is_locked() is True
                # Should raise PaymentDBLockAcquireError when lock1 is not released
                await asyncio.sleep(2)
                async with PaymentDBLock(payout_lock_repo, lock_id):
                    assert await lock1.is_locked() is True
        assert await lock1.is_locked() is False

    async def test_should_raise_exception_when_first_lock_try_to_release_but_the_same_lock_acquired_by_other_request(
        self, payout_lock_repo: PayoutLockRepository
    ):
        lock_id = self.lock_id
        original = self.counter

        async def acquire_lock_1():
            async with PaymentDBLock(payout_lock_repo, lock_id, ttl_sec=1):
                # Hold lock longer time than timeout
                await self.increase_counter()
                await asyncio.sleep(3)

        async def acquire_lock_2():
            # Wait for the first lock to time out (2s).
            await asyncio.sleep(2)
            async with PaymentDBLock(payout_lock_repo, lock_id, ttl_sec=2):
                await self.increase_counter()
                await asyncio.sleep(2)

        result1, result2 = await asyncio.gather(
            acquire_lock_1(), acquire_lock_2(), return_exceptions=True
        )
        # result1 should be PaymentDBLockReleaseError
        assert type(result1) == PaymentDBLockReleaseError
        assert result1.error_code == PaymentDBLockErrorCode.LOCK_RELEASE_ERROR
        assert (
            result1.error_message
            == payment_db_lock_error_message_maps[
                PaymentDBLockErrorCode.LOCK_RELEASE_ERROR
            ]
        )
        assert result2 is None
        assert self.counter == original + 2

    async def test_concurrent_lock_requests(
        self, payout_lock_repo: PayoutLockRepository
    ):
        lock_id = self.lock_id

        original = self.counter

        async def lock(lockable_db: Lockable, current_lock_id: str):
            async with PaymentDBLock(lockable_db, current_lock_id):
                await self.increase_counter()
                await asyncio.sleep(5)

        async def concurrent_acquire_payout_lock():
            requests = []
            for i in range(1000):
                requests.append(lock(payout_lock_repo, lock_id))

            results = await asyncio.gather(*requests, return_exceptions=True)
            for idx, val in enumerate(results):
                if idx == 0:
                    assert val is None
                    assert self.counter == original + 1
                else:
                    assert type(val) == PaymentDBLockAcquireError
                    assert val.error_code == PaymentDBLockErrorCode.LOCK_ACQUIRE_ERROR
                    assert (
                        val.error_message
                        == payment_db_lock_error_message_maps[
                            PaymentDBLockErrorCode.LOCK_ACQUIRE_ERROR
                        ]
                    )
                    assert self.counter == original + 1

        await concurrent_acquire_payout_lock()

    async def increase_counter(self):
        self.counter = self.counter + 1
