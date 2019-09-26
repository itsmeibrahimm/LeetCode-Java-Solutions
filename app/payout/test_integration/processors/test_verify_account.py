import asyncio
from unittest.mock import Mock

import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.config.app_config import AppConfig
from app.commons.database.infra import DB
from app.commons.providers.stripe.stripe_client import StripeAsyncClient, StripeClient
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import (
    StripeClientSettings,
    CreateAccountRequest,
    UpdateAccountRequest,
)
from app.commons.types import CountryCode
from app.commons.utils.pool import ThreadPoolHelper
from app.payout.core.account.processors.verify_account import (
    VerifyPayoutAccountRequest,
    VerifyPayoutAccount,
)
from app.payout.core.account.types import PayoutAccountInternal
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_stripe_managed_account,
    mock_stripe_account,
    mock_updated_stripe_account,
)

import stripe.error as stripe_error


class TestVerifyPayoutAccount:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

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

    async def test_verify_payout_account_create(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        test_account_token = "test_stripe_account_token"
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )

        request = VerifyPayoutAccountRequest(
            payout_account_id=payment_account.id,
            account_token=test_account_token,
            country=CountryCode.US,
        )
        verify_account_op = VerifyPayoutAccount(
            logger=mocker.Mock(),
            payment_account_repo=payment_account_repo,
            request=request,
            stripe_client=stripe_async_client,
        )

        stripe_account_id = "acct_test_stripe_account"
        stripe_account = mock_stripe_account(stripe_account_id=stripe_account_id)
        create_account_request = CreateAccountRequest(
            country=CountryCode.US, account_token=test_account_token
        )

        @asyncio.coroutine
        def mock_create_stripe_account(*args, **kwargs):
            return stripe_account

        mock_create_account: Mock = mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_account",
            side_effect=mock_create_stripe_account,
        )
        verified_payout_account: PayoutAccountInternal = await verify_account_op._execute()
        assert mock_create_account.called
        args, kwargs = mock_create_account.call_args
        assert kwargs["request"] == create_account_request
        assert verified_payout_account.payment_account.id == payment_account.id
        assert verified_payout_account.pgp_external_account_id == stripe_account_id
        assert (
            verified_payout_account.payment_account.statement_descriptor
            == "test_statement_descriptor"
        )

    async def test_verify_payout_account_throw_stripe_exception(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        test_account_token = "test_stripe_account_token"
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )

        request = VerifyPayoutAccountRequest(
            payout_account_id=payment_account.id,
            account_token=test_account_token,
            country=CountryCode.US,
        )
        verify_account_op = VerifyPayoutAccount(
            logger=mocker.Mock(),
            payment_account_repo=payment_account_repo,
            request=request,
            stripe_client=stripe_async_client,
        )

        @asyncio.coroutine
        def mock_create_stripe_account(*args, **kwargs):
            raise stripe_error.InvalidRequestError(
                message="invalid request",
                param=None,
                json_body={"error": {"message": "test StripeError"}},
            )

        mock_create_account: Mock = mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_account",
            side_effect=mock_create_stripe_account,
        )
        with pytest.raises(PayoutError) as e:
            await verify_account_op._execute()
        assert mock_create_account.called
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.PGP_ACCOUNT_NOT_FOUND
        assert e.value.error_message == "test StripeError"

    async def test_verify_payout_account_update(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        test_account_token = "test_stripe_account_token"
        stripe_account_id = "acct_update_stripe_account"

        # prepare Stripe Managed Account and insert, then validate
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo, stripe_id=stripe_account_id
        )

        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=sma.id
        )

        request = VerifyPayoutAccountRequest(
            payout_account_id=payment_account.id,
            account_token=test_account_token,
            country=CountryCode.US,
        )
        verify_account_op = VerifyPayoutAccount(
            logger=mocker.Mock(),
            payment_account_repo=payment_account_repo,
            request=request,
            stripe_client=stripe_async_client,
        )
        stripe_account = mock_updated_stripe_account(
            stripe_account_id=stripe_account_id
        )
        create_account_request = UpdateAccountRequest(
            id=stripe_account_id,
            country=CountryCode.US,
            account_token=test_account_token,
        )

        @asyncio.coroutine
        def mock_update_stripe_account(*args, **kwargs):
            return stripe_account

        mock_update_account: Mock = mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.update_account",
            side_effect=mock_update_stripe_account,
        )
        verified_payout_account: PayoutAccountInternal = await verify_account_op._execute()
        assert mock_update_account.called
        args, kwargs = mock_update_account.call_args
        assert kwargs["request"] == create_account_request
        assert verified_payout_account.payment_account.id == payment_account.id
        assert verified_payout_account.pgp_external_account_id == stripe_account_id
        assert (
            verified_payout_account.payment_account.statement_descriptor
            == "test_statement_descriptor"
        )
