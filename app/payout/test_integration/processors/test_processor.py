import asyncio
from unittest.mock import Mock

import pytest
import pytest_mock
from datetime import datetime, timezone

from app.commons.cache.utils import compose_cache_key
from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext
from app.commons.cache.cache import setup_cache, get_cache, PaymentCache
from app.commons.operational_flags import ENABLED_KEY_PREFIX_LIST_FOR_CACHE
from app.commons.providers.stripe import stripe_models
from app.commons.providers.stripe.stripe_client import (
    StripeTestClient,
    StripeClient,
    StripeAsyncClient,
)
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import (
    CreateAccountTokenMetaDataRequest,
    StripeClientSettings,
)
from app.commons.test_integration.utils import (
    prepare_and_validate_stripe_account_token,
    prepare_and_validate_stripe_account,
)
from app.commons.types import CountryCode
from app.commons.utils.pool import ThreadPoolHelper
from app.conftest import RuntimeSetter
from app.payout.constants import (
    PAYOUT_CACHE_APP_NAME,
    CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
)
from app.payout.core.account.processor import PayoutAccountProcessors
from app.payout.core.account.processors.get_account import GetPayoutAccountRequest
from app.payout.core.account.processors.update_account_statement_descriptor import (
    UpdatePayoutAccountStatementDescriptorRequest,
)
from app.payout.core.account.processors.verify_account import VerifyPayoutAccountRequest
from app.payout.models import AccountType
from app.payout.repository.maindb.model.payment_account import (
    PaymentAccountCreate,
    PaymentAccountUpdate,
    PaymentAccount,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountCreate,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
import app.payout.core.account.models as account_models
from app.payout.test_integration.utils import mock_updated_stripe_account


class TestProcessor:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def cache(self, app_context: AppContext):
        setup_cache(app_context=app_context, app=PAYOUT_CACHE_APP_NAME)
        return get_cache(app=PAYOUT_CACHE_APP_NAME)

    @pytest.fixture
    def stripe_async_client(self, app_config: AppConfig):
        stripe_client = StripeClient(
            settings_list=[
                StripeClientSettings(
                    api_key=app_config.STRIPE_US_SECRET_KEY.value, country="US"
                )
            ],
            http_client=TimedRequestsClient(),
        )

        stripe_thread_pool = ThreadPoolHelper(
            max_workers=app_config.STRIPE_MAX_WORKERS, prefix="stripe"
        )

        stripe_async_client = StripeAsyncClient(
            executor_pool=stripe_thread_pool, stripe_client=stripe_client
        )
        yield stripe_async_client
        stripe_thread_pool.shutdown()

    @pytest.fixture
    def payout_account_processor(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        cache: PaymentCache,
        stripe_async_client: StripeAsyncClient,
    ) -> PayoutAccountProcessors:
        return PayoutAccountProcessors(
            logger=mocker.Mock(),
            payment_account_repo=payment_account_repo,
            payment_account_edit_history_repo=mocker.Mock(),
            payout_card_repo=mocker.Mock(),
            payout_method_repo=mocker.Mock(),
            payout_method_miscellaneous_repo=mocker.Mock(),
            stripe_transfer_repo=mocker.Mock(),
            stripe_payout_request_repo=mocker.Mock(),
            stripe_managed_account_transfer_repo=mocker.Mock(),
            stripe=stripe_async_client,
            managed_account_transfer_repo=mocker.Mock(),
            cache=cache,
        )

    @pytest.fixture
    async def payout_account(
        self,
        payment_account_repo: PaymentAccountRepository,
        stripe_test: StripeTestClient,
    ) -> PaymentAccount:
        data = PaymentAccountCreate(
            account_type=AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT,
            entity="dasher",
            resolve_outstanding_balance_frequency="daily",
            payout_disabled=True,
            charges_enabled=True,
            old_account_id=1234,
            upgraded_to_managed_account_at=datetime.now(timezone.utc),
            is_verified_with_stripe=True,
            transfers_enabled=True,
            statement_descriptor="test_statement_descriptor",
        )
        created_account = await payment_account_repo.create_payment_account(data)
        assert created_account.id, "id shouldn't be None"
        assert created_account.created_at, "created_at shouldn't be None"

        create_account_token_data = CreateAccountTokenMetaDataRequest(
            business_type="individual",
            individual=stripe_models.Individual(
                first_name="Test",
                last_name="Payment",
                dob=stripe_models.DateOfBirth(day=1, month=1, year=1990),
                address=stripe_models.Address(
                    city="Mountain View",
                    country=CountryCode.US.value,
                    line1="123 Castro St",
                    line2="",
                    postal_code="94041",
                    state="CA",
                ),
                ssn_last_4="1234",
            ),
            tos_shown_and_accepted=True,
        )
        account_token = prepare_and_validate_stripe_account_token(
            stripe_client=stripe_test, data=create_account_token_data
        )
        account = prepare_and_validate_stripe_account(stripe_test, account_token)
        sma_data = StripeManagedAccountCreate(
            stripe_id=account.stripe_id,
            country_shortname="US",
            fingerprint="fingerprint",
            verification_disabled_reason="no-reason",
        )
        sma = await payment_account_repo.create_stripe_managed_account(sma_data)
        await payment_account_repo.update_payment_account_by_id(
            created_account.id, PaymentAccountUpdate(account_id=sma.id)
        )
        return created_account

    async def test_get_payout_account(
        self,
        cache: PaymentCache,
        payout_account_processor,
        payout_account: PaymentAccount,
        runtime_setter: RuntimeSetter,
    ):
        runtime_setter.set(
            ENABLED_KEY_PREFIX_LIST_FOR_CACHE, [CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT]
        )
        # check cache before calling get_payout_account
        request = GetPayoutAccountRequest(payout_account_id=payout_account.id)
        composed_cache_key = compose_cache_key(
            CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
            (payout_account_processor,),
            {"request": request},
            True,
        )
        assert not await cache.exist(key=composed_cache_key)
        payout_account_internal = await payout_account_processor.get_payout_account(
            request=request
        )
        assert payout_account_internal
        assert payout_account_internal.payment_account.id == payout_account.id

        # check cache after calling get_payout_account
        assert await cache.exist(key=composed_cache_key)
        cached_result = await cache.get(key=composed_cache_key)
        deserialized_payout_account_internal = account_models.PayoutAccountInternal.parse_raw(
            cached_result
        )
        assert payout_account_internal == deserialized_payout_account_internal

        # call get_payout_account again should fetch from cache
        payout_account_internal_again = await payout_account_processor.get_payout_account(
            request=request
        )
        assert payout_account_internal == payout_account_internal_again

        # invalidate cache and set feature flag to False
        await cache.invalidate(key=composed_cache_key)
        runtime_setter.set(ENABLED_KEY_PREFIX_LIST_FOR_CACHE, [])
        payout_account_internal_with_feature_flag_disabled = await payout_account_processor.get_payout_account(
            request=request
        )
        assert not await cache.exist(key=composed_cache_key)
        assert (
            payout_account_internal_with_feature_flag_disabled
            == payout_account_internal
        )

    async def test_update_payout_account_statement_descriptor(
        self,
        cache: PaymentCache,
        payout_account_processor,
        payout_account: PaymentAccount,
        runtime_setter: RuntimeSetter,
    ):
        runtime_setter.set(
            ENABLED_KEY_PREFIX_LIST_FOR_CACHE, [CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT]
        )
        # check cache before calling get_payout_account
        request = GetPayoutAccountRequest(payout_account_id=payout_account.id)
        composed_cache_key_for_get = compose_cache_key(
            CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
            (payout_account_processor,),
            {"request": request},
            True,
        )
        print("here composed cache key " + composed_cache_key_for_get)
        assert not await cache.exist(key=composed_cache_key_for_get)

        # call get_payout_account should set cache
        payout_account_internal = await payout_account_processor.get_payout_account(
            request=request
        )
        assert payout_account_internal
        assert payout_account_internal.payment_account.id == payout_account.id

        # check cache after calling get_payout_account
        assert await cache.exist(key=composed_cache_key_for_get)

        # call update_payout_account_statement_descriptor should invalidate cache
        new_statement_descriptor = "new_statement_descriptor"
        request_update_statement_descriptor = UpdatePayoutAccountStatementDescriptorRequest(
            payout_account_id=payout_account.id,
            statement_descriptor="new_statement_descriptor",
        )
        payout_account_internal_updated = await payout_account_processor.update_payout_account_statement_descriptor(
            request=request_update_statement_descriptor
        )
        composed_cache_key_for_update = compose_cache_key(
            CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
            (payout_account_processor,),
            {"request": request_update_statement_descriptor},
            True,
        )
        assert composed_cache_key_for_get == composed_cache_key_for_update
        assert (
            payout_account_internal_updated.payment_account.statement_descriptor
            == new_statement_descriptor
        )
        assert not await cache.exist(key=composed_cache_key_for_get)
        assert not await cache.exist(key=composed_cache_key_for_update)

    async def test_verify_payout_account(
        self,
        mocker: pytest_mock.MockFixture,
        cache: PaymentCache,
        payout_account_processor,
        payout_account: PaymentAccount,
        stripe_test: StripeTestClient,
        runtime_setter: RuntimeSetter,
    ):
        runtime_setter.set(
            ENABLED_KEY_PREFIX_LIST_FOR_CACHE, [CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT]
        )
        # check cache before calling get_payout_account
        request = GetPayoutAccountRequest(payout_account_id=payout_account.id)
        composed_cache_key_for_get = compose_cache_key(
            CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
            (payout_account_processor,),
            {"request": request},
            True,
        )
        print("here composed cache key " + composed_cache_key_for_get)
        assert not await cache.exist(key=composed_cache_key_for_get)

        # call get_payout_account should set cache
        payout_account_internal = await payout_account_processor.get_payout_account(
            request=request
        )
        assert payout_account_internal
        assert payout_account_internal.payment_account.id == payout_account.id

        # check cache after calling get_payout_account
        assert await cache.exist(key=composed_cache_key_for_get)

        # call verify_payout_account should invalidate cache
        test_account_token = "test_stripe_account_token"
        request_verify_payout_account = VerifyPayoutAccountRequest(
            payout_account_id=payout_account.id,
            country=CountryCode.US,
            account_token=test_account_token,
        )
        stripe_account_id = "acct_test_stripe_account"
        stripe_account = mock_updated_stripe_account(
            stripe_account_id=stripe_account_id
        )

        @asyncio.coroutine
        def mock_update_stripe_account(*args, **kwargs):
            return stripe_account

        mock_update_account: Mock = mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.update_account",
            side_effect=mock_update_stripe_account,
        )

        payout_account_internal_updated = await payout_account_processor.verify_payout_account(
            request=request_verify_payout_account
        )
        composed_cache_key_for_update = compose_cache_key(
            CACHE_KEY_PREFIX_GET_PAYOUT_ACCOUNT,
            (payout_account_processor,),
            {"request": request_verify_payout_account},
            True,
        )
        assert mock_update_account.called
        assert composed_cache_key_for_get == composed_cache_key_for_update
        assert payout_account_internal_updated.pgp_external_account_id
        assert not await cache.exist(key=composed_cache_key_for_get)
        assert not await cache.exist(key=composed_cache_key_for_update)
