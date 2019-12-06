import asyncio

import pytest
from aredis.cache import Cache

from app.commons.context.app_context import AppContext
from app.payout.core.account import models as account_models
from app.payout.repository.maindb.model.payment_account import PaymentAccount


class TestRedisCluster:
    pytestmark = [pytest.mark.asyncio]

    async def test_redis_cluster(self, app_context: AppContext):
        key = "payment_account_id"
        value = 1
        await app_context.redis_cluster.set(key, value)
        assert await app_context.redis_cluster.exists(key)
        actual_value = await app_context.redis_cluster.get(key)
        assert actual_value.decode("utf-8") == str(value)

        key = "payment_account_1"
        value = account_models.PayoutAccountInternal(
            payment_account=PaymentAccount(
                id=1, statement_descriptor="test_statement_descriptor"
            ),
            pgp_external_account_id=1,
            verification_requirements=None,
        ).to_string()
        await app_context.redis_cluster.set(key, value)
        assert await app_context.redis_cluster.exists(key)
        actual_value = await app_context.redis_cluster.get(key)
        assert actual_value.decode("utf-8") == value
        await app_context.redis_cluster.expire(key, 1)
        await asyncio.sleep(0.1)
        assert await app_context.redis_cluster.ttl(key) > 0
        await asyncio.sleep(1)
        assert not await app_context.redis_cluster.exists(key)

    async def test_cache(self, app_context: AppContext):
        cache = Cache(app_context.redis_cluster, app="PaymentService")
        key = "payment_account_id"
        value = 1
        await cache.set(key, value)
        assert await cache.exist(key)
        actual_value = await cache.get(key)
        assert actual_value == value

        key = "payment_account_1"
        value = account_models.PayoutAccountInternal(
            payment_account=PaymentAccount(
                id=1, statement_descriptor="test_statement_descriptor"
            ),
            pgp_external_account_id=1,
            verification_requirements=None,
        ).to_string()
        await cache.set(key, value, expire_time=1)
        assert await cache.exist(key)
        actual_value = await cache.get(key)
        assert actual_value == value
        await asyncio.sleep(0.1)
        assert await cache.ttl(key) > 0
        await asyncio.sleep(1)
        assert not await app_context.redis_cluster.exists(key)
