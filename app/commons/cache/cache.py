import asyncio
import functools
from typing import Optional

from aredis.cache import Cache
from aredis import StrictRedisCluster, RedisError
from doordash_python_stats.ddstats import doorstats_global
from structlog.stdlib import BoundLogger

from app.commons.cache.utils import compose_cache_key, is_cacheable, is_instance_method
from app.commons.context.app_context import AppContext
from app.commons.context.logger import get_logger
from app.commons.core.errors import PaymentCacheIsNotInitialized
from app.payout.constants import (
    PAYMENT_CACHE_DECORATOR_MISS_STATS_PREFIX,
    PAYMENT_CACHE_DECORATOR_HIT_STATS_PREFIX,
    PAYMENT_CACHE_HIT_STATS_PREFIX,
    PAYMENT_CACHE_MISS_STATS_PREFIX,
)
from app.payout.core.feature_flags import enabled_cache_key_prefix_list

logger = get_logger("cache")

DEFAULT_CACHE_APP_NAME = "payment-service"

caches = {}


class PaymentCache:
    logger: BoundLogger
    cache: Cache

    def __init__(self, redis_cluster: StrictRedisCluster, app: str):
        self.logger = logger
        self.cache = Cache(redis_cluster, app=app)

    async def set(self, key, value, ttl_sec: int = 5, param=None):
        try:
            await self.cache.set(key=key, value=value, expire_time=ttl_sec, param=param)
        except Exception as e:
            logger.error(
                "Set cache failed", key=key, value=value, ttl=ttl_sec, error=str(e)
            )

    async def get(self, key, param=None):
        try:
            result = await self.cache.get(key=key, param=param)
            if result:
                doorstats_global.incr(PAYMENT_CACHE_HIT_STATS_PREFIX.format(key))
            else:
                doorstats_global.incr(PAYMENT_CACHE_MISS_STATS_PREFIX.format(key))
            return result
        except RedisError as e:
            logger.error("Get cache failed", key=key, error=str(e))

    async def invalidate(self, key, param=None):
        try:
            return await self.cache.delete(key=key, param=param)
        except RedisError as e:
            logger.error("Invalidate cache failed", key=key, error=str(e))

    async def exist(self, key, param=None):
        try:
            return await self.cache.exist(key=key, param=param)
        except RedisError as e:
            logger.error("Check the existence for cache failed", key=key, error=str(e))


def setup_cache(app_context: AppContext, app: str = DEFAULT_CACHE_APP_NAME):
    default_cache = PaymentCache(redis_cluster=app_context.redis_cluster, app=app)
    caches[app] = default_cache
    return default_cache


def get_cache(app) -> Optional[PaymentCache]:
    if app in caches:
        return caches[app]
    else:
        logger.error("cache is not initialized yet")
        return None


# decorator to call cache.get
# key: cache key
# expire_time: ttl in seconds
# app: app name used to calculate the unique identity of a cache entry
def cached(
    key,
    ttl_sec=5,
    app=DEFAULT_CACHE_APP_NAME,
    param=None,
    cache=None,
    response_model=None,
):
    assert isinstance(ttl_sec, int)

    def _decorator(func):
        cache_wrapper = CacheWrapper(
            func=func,
            key=key,
            expire_time=ttl_sec,
            app=app,
            param=param,
            cache=cache,
            response_model=response_model,
        )
        # call async wrapper
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await cache_wrapper.get(args=args, kwargs=kwargs)

        return async_wrapper

    return _decorator


class CacheWrapper(object):
    def __init__(
        self,
        func,
        key,
        expire_time=5,
        app=DEFAULT_CACHE_APP_NAME,
        param=None,
        cache=None,
        response_model=None,
    ):
        self.func = func
        self.key = key
        self.app = app
        self.expire_time = expire_time
        self.param = param
        self.app = app
        self.cache = cache if cache else get_cache(app=self.app)
        self.cls = response_model
        self.__name__ = func.__name__
        self.__module__ = func.__module__

    async def get(self, args, kwargs):
        cache_enabled_list = enabled_cache_key_prefix_list()
        # cache is not enabled for self.key
        if not (self.key in cache_enabled_list):
            # call the original function
            return await self._call_func(args, kwargs)

        if not self.cache:
            self.cache = get_cache(self.app)

        if not self.cache:
            raise PaymentCacheIsNotInitialized

        is_method = False
        composed_cache_key = self.key
        try:
            if is_instance_method(self.func):
                is_method = True
            composed_cache_key = compose_cache_key(
                key=self.key,
                args=args,
                kwargs=kwargs,
                use_hash=True,
                is_method=is_method,
            )
            cached_result = await self.cache.get(
                key=composed_cache_key, param=self.param
            )
            if self.cls and cached_result:
                result = self.cls.deserialize(cached_result)
            else:
                result = cached_result
        except Exception as e:
            logger.error(
                "Get cache failed {}_{}".format(self.__module__, self.__name__),
                key=self.key,
                error=str(e),
            )
            result = None

        # cache missing
        if not result:
            logger.info(
                "Missing cache", composed_cache_key=composed_cache_key, key=self.key
            )
            doorstats_global.incr(
                PAYMENT_CACHE_DECORATOR_MISS_STATS_PREFIX.format(self.key)
            )
            result = await self._call_func(args, kwargs)

            if not is_cacheable(result):
                logger.error(
                    "Data type is not cacheable {}_{}".format(
                        self.__module__, self.__name__
                    ),
                    key=self.key,
                    value=result,
                )
                return result

            if self.cls:
                cached_data = self.cls.serialize(result)
            else:
                cached_data = result

            try:
                await self.cache.set(
                    key=composed_cache_key,
                    value=cached_data,
                    ttl_sec=self.expire_time,
                    param=self.param,
                )
            except RedisError as e:
                logger.error(
                    "Set cache failed {}_{}".format(self.__module__, self.__name__),
                    key=self.key,
                    value=result,
                    error=str(e),
                )
        else:
            doorstats_global.incr(
                PAYMENT_CACHE_DECORATOR_HIT_STATS_PREFIX.format(self.key)
            )

        return result

    async def _call_func(self, args, kwargs):
        try:
            if asyncio.iscoroutinefunction(self.func):
                result = await self.func(*args, **kwargs)
            else:
                result = self.func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(
                "Called func failed in cached {}_{}".format(
                    self.__module__, self.__name__
                ),
                error=str(e),
            )
            raise
