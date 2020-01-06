import asyncio

import pytest

from app.commons.context.app_context import AppContext
from app.commons.cache.cache import setup_cache, get_cache, PaymentCache, cached
from app.commons.cache.utils import compose_cache_key
from app.commons.operational_flags import ENABLED_KEY_PREFIX_LIST_FOR_CACHE
from app.conftest import RuntimeSetter
from app.payout.constants import CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT
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
        assert not await cache.get(key=key_str)

    async def test_decorator_func(
        self, cache: PaymentCache, runtime_setter: RuntimeSetter
    ):
        runtime_setter.set(
            ENABLED_KEY_PREFIX_LIST_FOR_CACHE, [CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT]
        )
        payment_account_id_a = 1

        @cached(key=CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT, ttl_sec=1, app="test_payment")
        def get_payment_account(payout_account_id):
            return account_models.PayoutAccountInternal(
                payment_account=PaymentAccount(
                    id=payout_account_id,
                    statement_descriptor="test_statement_descriptor",
                ),
                pgp_external_account_id=1,
                verification_requirements=None,
            ).to_string()

        composed_cache_key = compose_cache_key(
            key=CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
            args=(payment_account_id_a,),
            kwargs={},
            use_hash=True,
            is_method=False,
        )
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
        composed_cache_key_b = compose_cache_key(
            key=CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
            args=(payment_account_id_b,),
            kwargs={},
            use_hash=True,
            is_method=False,
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

    async def test_decorator_method(
        self, cache: PaymentCache, runtime_setter: RuntimeSetter
    ):
        runtime_setter.set(
            ENABLED_KEY_PREFIX_LIST_FOR_CACHE, [CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT]
        )
        payment_account_id_a = 1

        class TestObject:
            @cached(
                key=CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT, ttl_sec=1, app="test_payment"
            )
            def get_payment_account(self, payout_account_id):
                return account_models.PayoutAccountInternal(
                    payment_account=PaymentAccount(
                        id=payout_account_id,
                        statement_descriptor="test_statement_descriptor",
                    ),
                    pgp_external_account_id=1,
                    verification_requirements=None,
                ).to_string()

        # get composed key for an instance method
        test_object = TestObject()
        composed_cache_key = compose_cache_key(
            key=CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
            args=(test_object,),
            kwargs={"payout_account_id": payment_account_id_a},
            use_hash=True,
            is_method=True,
        )

        # check cache before calling instance method
        assert cache
        await cache.invalidate(key=composed_cache_key)
        assert not await cache.exist(key=composed_cache_key)

        await test_object.get_payment_account(payout_account_id=payment_account_id_a)

        assert await cache.exist(key=composed_cache_key)

    async def test_decorator_with_feature_flag_disabled(
        self, cache: PaymentCache, runtime_setter: RuntimeSetter
    ):
        runtime_setter.set(ENABLED_KEY_PREFIX_LIST_FOR_CACHE, [])

        class TestObject:
            class ArgT:
                def __init__(self, value):
                    self.value = value

                def foo(self):
                    return self.value

            @cached(
                key=CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT, ttl_sec=1, app="test_payment"
            )
            def get_payment_account(self, arg: ArgT):
                return account_models.PayoutAccountInternal(
                    payment_account=PaymentAccount(
                        id=arg.foo(), statement_descriptor="test_statement_descriptor"
                    ),
                    pgp_external_account_id=1,
                    verification_requirements=None,
                ).to_string()

        request = TestObject.ArgT(1)

        # get composed key for an instance method
        test_object = TestObject()
        composed_cache_key = compose_cache_key(
            key=CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
            args=(test_object,),
            kwargs={"arg": request},
            use_hash=True,
            is_method=True,
        )

        # check cache before calling instance method
        assert cache
        await cache.invalidate(key=composed_cache_key)
        assert not await cache.exist(key=composed_cache_key)

        await test_object.get_payment_account(arg=request)
        assert not await cache.exist(key=composed_cache_key)
