import asyncio

import pytest
import pytest_mock

from app.commons.config.app_config import AppConfig
from app.commons.database.infra import DB
from app.commons.providers.stripe.stripe_client import StripeAsyncClient, StripeClient
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import (
    Account,
    Individual,
    Address,
    DateOfBirth,
    StripeClientSettings,
)
from app.commons.types import CountryCode, Currency
from app.commons.utils.pool import ThreadPoolHelper
from app.payout.core.account.processors.verify_account import (
    VerifyPayoutAccountRequest,
    VerifyPayoutAccount,
)
from app.payout.core.account.types import PayoutAccountInternal
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import prepare_and_insert_payment_account


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

    async def test_verify_payout_account(
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
            stripe=stripe_async_client,
        )

        stripe_account_id = "acct_test_stripe_account"
        stripe_account = Account(
            id=stripe_account_id,
            object="Account",
            business_type="individual",
            charges_enabled=True,
            country=CountryCode.US,
            default_currency=Currency.USD,
            company=None,
            individual=Individual(
                address=Address(
                    city="Mountain View",
                    country="US",
                    line1="123 Castro St",
                    line2="",
                    postal_code="94041",
                    state="CA",
                ),
                dob=DateOfBirth(day=1, month=4, year=1990),
                email=None,
                first_name="test",
                last_name="payout",
                id_number=None,
                phone=None,
                ssn_last_4=None,
                verification=None,
            ),
            details_submitted=False,
            email=None,
        )

        @asyncio.coroutine
        def mock_create_stripe_account(*args, **kwargs):
            return stripe_account

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_stripe_account",
            side_effect=mock_create_stripe_account,
        )
        verified_payout_account: PayoutAccountInternal = await verify_account_op._execute()
        assert verified_payout_account.payment_account.id == payment_account.id
        assert verified_payout_account.pgp_external_account_id == stripe_account_id
        assert (
            verified_payout_account.payment_account.statement_descriptor
            == "test_statement_descriptor"
        )
