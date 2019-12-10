import asyncio
import functools
import hashlib

import six
from aredis.cache import Cache
from aredis import StrictRedisCluster, RedisError
from structlog.stdlib import BoundLogger

from app.commons.context.app_context import AppContext
from app.commons.context.logger import get_logger
from app.commons.core.errors import (
    PaymentCacheGetError,
    PaymentCacheSetError,
    PaymentCacheInvalidateError,
    PaymentCacheCheckExistenceError,
)

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
        except RedisError as e:
            logger.error(
                "Set cache failed", key=key, value=value, ttl=ttl_sec, error=str(e)
            )
            raise PaymentCacheSetError() from e

    async def get(self, key, param=None):
        try:
            return await self.cache.get(key=key, param=param)
        except RedisError as e:
            logger.error("Get cache failed", key=key, error=str(e))
            raise PaymentCacheGetError() from e

    async def invalidate(self, key, param=None):
        try:
            return await self.cache.delete(key=key, param=param)
        except RedisError as e:
            logger.error("Invalidate cache failed", key=key, error=str(e))
            raise PaymentCacheInvalidateError() from e

    async def exist(self, key, param=None):
        try:
            return await self.cache.exist(key=key, param=param)
        except RedisError as e:
            logger.error("Check the existence for cache failed", key=key, error=str(e))
            raise PaymentCacheCheckExistenceError() from e


def setup_cache(app_context: AppContext, app: str = DEFAULT_CACHE_APP_NAME):
    default_cache = PaymentCache(redis_cluster=app_context.redis_cluster, app=app)
    caches[app] = default_cache


def get_cache(app):
    return caches[app]


# decorator to call cache.get
# key: cache key
# expire_time: ttl in seconds
# app: app name used to calculate the unique identity of a cache entry
def cached(key, ttl=5, app=DEFAULT_CACHE_APP_NAME, param=None):
    assert isinstance(ttl, int)

    def _decorator(func):
        cache_wrapper = CacheWrapper(
            func=func, key=key, expire_time=ttl, app=app, param=param
        )
        # call async wrapper
        @functools.wraps(func)
        async def sync_wrapper(*args, **kwargs):
            return await cache_wrapper.get(args=args, kwargs=kwargs)

        return sync_wrapper

    return _decorator


class CacheWrapper(object):
    def __init__(
        self, func, key, expire_time=5, app=DEFAULT_CACHE_APP_NAME, param=None
    ):
        self.func = func
        self.key = key
        self.app = app
        self.expire_time = expire_time
        self.param = param
        self.app = app
        self.cache = get_cache(app=self.app)
        self.__name__ = func.__name__
        self.__module__ = func.__module__

    async def get(self, args, kwargs):
        try:
            composed_cache_key = composed_cache_key_from_args(
                key=self.key, args=args, kwargs=kwargs, use_hash=True
            )
            result = await self.cache.get(key=composed_cache_key, param=self.param)
        except RedisError as e:
            logger.error("Get cache failed", key=self.key, error=str(e))
            raise PaymentCacheGetError() from e

        # cache missing
        if not result:
            if asyncio.iscoroutinefunction(self.func):
                result = await self.func(*args, **kwargs)
            else:
                result = self.func(*args, **kwargs)
            try:
                await self.cache.set(
                    key=composed_cache_key,
                    value=result,
                    ttl_sec=self.expire_time,
                    param=self.param,
                )
            except RedisError as e:
                logger.error(
                    "Set cache failed", key=self.key, value=result, error=str(e)
                )
                raise PaymentCacheSetError() from e
        return result


def safe_unicode(value, encoding="utf-8"):
    if isinstance(value, six.text_type):
        return value
    elif isinstance(value, six.binary_type):
        try:
            value = six.text_type(value, encoding)
        except UnicodeDecodeError:
            value = value.decode("utf-8", "replace")

    return value


def composed_cache_key_from_args(key=None, args=None, kwargs=None, use_hash=True):
    """
    Turn functions args into some sort of string. It doesn't matter too much what it looks like,
    since we are going to hash it anyway, so long as it is predictable and unique.
    NOTE: using 'args' is kind of deprecated, since @cached won't use it. It might still be useful
    for other stuff though.
    """
    components = [key]

    # Note that repr() returns UTF-8 strings
    if args:
        args_fixed = [safe_unicode(arg) for arg in args]
        args_str = safe_unicode(repr(args_fixed))
        components.append(args_str)
    if kwargs:
        kwargs_fixed = {key: safe_unicode(val) for key, val in sorted(kwargs.items())}
        kwargs_str = safe_unicode(repr(kwargs_fixed))
        components.append(kwargs_str)

    # This is unicode
    arg_str = "".join(components)
    if use_hash:
        # Convert to utf-8 for hashlib to work
        arg_str = arg_str.encode("utf-8")
        arg_str = hashlib.sha256(arg_str).hexdigest()

    # Return unicode again
    return safe_unicode(arg_str)
