import asyncio
import time
from aioredlock import LockError
import pytest
from asynctest import mock
from app.commons.context.app_context import AppContext
from app.commons.core.errors import (
    PaymentLockAcquireError,
    PaymentLockReleaseError,
    PaymentLockErrorCode,
    payment_lock_error_message_maps,
)
from app.commons.lock.locks import PaymentLock
from app.main import config
from aioredlock.redis import Redis


class TestPaymentLock:
    pytestmark = [pytest.mark.asyncio]

    def setup(self):
        self.lock_name = "payout_account_lock"

    @pytest.fixture
    def mock_set_lock(self):
        with mock.patch("aioredlock.redis.Redis.set_lock") as mock_set_lock:
            yield mock_set_lock

    async def test_successfully_acquire_lock(self, app_context: AppContext):
        async with PaymentLock(self.lock_name, app_context.redis_lock_manager) as lock:
            assert await lock.is_locked() is True
        assert await lock.is_locked() is False

    async def test_acquire_same_lock_when_first_lock_is_released(
        self, app_context: AppContext
    ):
        async with PaymentLock(self.lock_name, app_context.redis_lock_manager) as lock1:
            assert await lock1.is_locked() is True
        assert await lock1.is_locked() is False

        # Should successfully acquire same lock when first one is released
        async with PaymentLock(self.lock_name, app_context.redis_lock_manager) as lock2:
            assert await lock2.is_locked() is True
        assert await lock2.is_locked() is False

    async def test_acquire_same_lock_when_first_lock_is_not_released(
        self, app_context: AppContext
    ):
        async with PaymentLock(self.lock_name, app_context.redis_lock_manager) as lock1:
            assert await lock1.is_locked() is True
            # Should raise PaymentLockAcquireError when lock1 is not released
            with pytest.raises(PaymentLockAcquireError):
                async with PaymentLock(self.lock_name, app_context.redis_lock_manager):
                    pass
        assert await lock1.is_locked() is False

    async def test_setup_shorter_than_default_lock_timeout(
        self, app_context: AppContext
    ):
        assert (
            app_context.redis_lock_manager.lock_timeout
            == config.REDIS_LOCK_DEFAULT_TIMEOUT
        )
        new_timeout = 2
        async with PaymentLock(
            self.lock_name, app_context.redis_lock_manager, new_timeout
        ) as lock:
            assert await lock.is_locked() is True
            time.sleep(new_timeout + 1)
            assert await lock.is_locked() is False

    async def test_should_raise_exception_when_first_lock_timeout_and_same_lock_acquired_by_other_request(
        self, app_context: AppContext
    ):
        async def acquire_lock_1():
            async with PaymentLock(self.lock_name, app_context.redis_lock_manager, 2):
                # Hold lock longer time than timeout
                await asyncio.sleep(4)

        async def acquire_lock_2():
            # Wait for the first lock to time out (2s).
            await asyncio.sleep(3)
            async with PaymentLock(self.lock_name, app_context.redis_lock_manager, 2):
                await asyncio.sleep(3)

        result1, result2 = await asyncio.gather(
            acquire_lock_1(), acquire_lock_2(), return_exceptions=True
        )
        # result1 should be PaymentLockReleaseError
        assert type(result1) == PaymentLockReleaseError
        assert result1.error_code == PaymentLockErrorCode.LOCK_RELEASE_ERROR
        assert (
            result1.error_message
            == payment_lock_error_message_maps[PaymentLockErrorCode.LOCK_RELEASE_ERROR]
        )
        assert result2 is None

    @pytest.mark.skip(
        "Passed in local. Since it will wait for 10 seconds, disable in CI/CD."
    )
    async def test_setup_longer_than_default_lock_timeout(
        self, app_context: AppContext
    ):
        assert (
            app_context.redis_lock_manager.lock_timeout
            == config.REDIS_LOCK_DEFAULT_TIMEOUT
        )
        new_timeout = 15
        async with PaymentLock(
            self.lock_name, app_context.redis_lock_manager, new_timeout
        ) as lock:
            assert await lock.is_locked() is True
            time.sleep(config.REDIS_LOCK_DEFAULT_TIMEOUT + 1)
            assert await lock.is_locked() is True

    async def test_failed_to_connect_redis(
        self, app_context: AppContext, mock_set_lock
    ):
        # assert app_context is using default timeout and retry count
        assert (
            app_context.redis_lock_manager.lock_timeout
            == config.REDIS_LOCK_DEFAULT_TIMEOUT
        )
        assert app_context.redis_lock_manager.retry_count == config.REDIS_LOCK_MAX_RETRY

        # overwrite redis instances to some unknown address
        app_context.redis_lock_manager.redis = Redis(
            [("unknown_address", 1111)], config.REDIS_LOCK_DEFAULT_TIMEOUT
        )
        # Should raise PaymentLockAcquireError when can't connect to redis
        mock_set_lock.side_effect = LockError
        with pytest.raises(PaymentLockAcquireError):
            async with PaymentLock(self.lock_name, app_context.redis_lock_manager):
                pass

    async def test_setup_new_max_retry(self, app_context: AppContext, mock_set_lock):
        # assert app_context is using default timeout and retry count
        assert (
            app_context.redis_lock_manager.lock_timeout
            == config.REDIS_LOCK_DEFAULT_TIMEOUT
        )
        assert app_context.redis_lock_manager.retry_count == config.REDIS_LOCK_MAX_RETRY

        # overwrite redis instances to some unknown address
        app_context.redis_lock_manager.redis = Redis(
            [("unknown_address", 1111)], config.REDIS_LOCK_DEFAULT_TIMEOUT
        )
        mock_set_lock.side_effect = LockError
        new_max_retry = 5
        # Should raise PaymentLockAcquireError when can't connect to redis and retry time should be new_max_retry
        with pytest.raises(PaymentLockAcquireError):
            async with PaymentLock(
                self.lock_name, app_context.redis_lock_manager, None, new_max_retry
            ):
                pass

        assert mock_set_lock.call_count != config.REDIS_LOCK_MAX_RETRY
        assert mock_set_lock.call_count == new_max_retry
