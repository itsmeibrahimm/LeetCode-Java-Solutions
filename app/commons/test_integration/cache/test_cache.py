import asyncio

import pytest

from app.commons.context.app_context import AppContext
from app.commons.core.cache import (
    setup_cache,
    get_cache,
    PaymentCache,
    cached,
    composed_cache_key_from_args,
)
from app.payout.core.account import models as account_models
from app.payout.repository.maindb.model.payment_account import PaymentAccount


class TestCache:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def cache(self, app_context: AppContext):
        app = "test_payment"
        setup_cache(app_context=app_context, app=app)
        return get_cache(app=app)

    async def test_cache(self, cache: PaymentCache):
        # set int
        key = "payment_account_id"
        value = 1
        assert cache
        await cache.invalidate(key=key)
        await cache.set(key=key, value=value)
        assert await cache.exist(key=key)
        actual_value = await cache.get(key=key)
        assert actual_value == value

        # set a PaymentAccountInternal object
        key_pa = "payment_account_1"
        value_pa = account_models.PayoutAccountInternal(
            payment_account=PaymentAccount(
                id=1, statement_descriptor="test_statement_descriptor"
            ),
            pgp_external_account_id=1,
            verification_requirements=None,
        ).to_string()
        await cache.invalidate(key=key_pa)
        await cache.set(key=key_pa, value=value_pa, ttl_sec=1)
        assert await cache.exist(key=key_pa)
        actual_value_pa = await cache.get(key=key_pa)
        assert actual_value_pa == value_pa
        await asyncio.sleep(0.1)
        assert await cache.exist(key=key_pa)
        await asyncio.sleep(1)
        assert not await cache.exist(key=key_pa)

        # set a str
        key_str = "cache_test_string"
        value_str = "invalidate"
        await cache.invalidate(key=key_str)
        await cache.set(key=key_str, value=value_str)
        assert await cache.exist(key=key_str)
        await cache.invalidate(key=key_str)
        assert not await cache.exist(key=key_str)

    async def test_decorator(self, cache: PaymentCache):
        payment_account_id_a = 1
        key = "get_payment_account"
        composed_cache_key = composed_cache_key_from_args(
            key=key, args=(payment_account_id_a,), kwargs={}, use_hash=True
        )

        @cached(key=key, ttl=1, app="test_payment")
        def get_payment_account(payout_account_id):
            return account_models.PayoutAccountInternal(
                payment_account=PaymentAccount(
                    id=payout_account_id,
                    statement_descriptor="test_statement_descriptor",
                ),
                pgp_external_account_id=1,
                verification_requirements=None,
            ).to_string()

        # before calling get_payment_account
        assert cache
        await cache.invalidate(key=composed_cache_key)
        assert not await cache.exist(key=composed_cache_key)

        # call get_payment_account
        payment_account_internal = await get_payment_account(payment_account_id_a)

        # check cache
        await asyncio.sleep(0.1)
        assert await cache.exist(key=composed_cache_key)
        assert await cache.get(key=composed_cache_key) == payment_account_internal

        # insert another payment account into cache
        payment_account_id_b = 2
        composed_cache_key_b = composed_cache_key_from_args(
            key=key, args=(payment_account_id_b,), kwargs={}, use_hash=True
        )
        await cache.invalidate(key=composed_cache_key_b)
        assert not await cache.exist(key=composed_cache_key_b)

        # call get_payment_account
        payment_account_internal_b = await get_payment_account(payment_account_id_b)

        # check cache
        await asyncio.sleep(0.1)
        assert await cache.exist(key=composed_cache_key)
        assert await cache.exist(key=composed_cache_key_b)
        assert await cache.get(key=composed_cache_key_b) == payment_account_internal_b
        await asyncio.sleep(1)
        assert not await cache.exist(key=payment_account_internal_b)
        assert not await cache.exist(key=payment_account_internal)
