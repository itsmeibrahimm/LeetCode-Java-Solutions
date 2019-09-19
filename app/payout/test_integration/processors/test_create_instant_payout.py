import asyncio

import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.config.app_config import AppConfig
from app.commons.database.infra import DB
from app.commons.providers.stripe.stripe_client import StripeAsyncClient, StripeClient
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import StripeClientSettings, Transfer
from app.commons.utils.pool import ThreadPoolHelper
from app.payout.core.account.processors.create_instant_payout import (
    CreateInstantPayout,
    CreateInstantPayoutRequest,
)
from app.payout.core.exceptions import (
    PayoutError,
    PayoutErrorCode,
    payout_error_message_maps,
)
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepository,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepository,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_stripe_managed_account,
    prepare_and_insert_payment_account,
)
from app.payout.types import PayoutType


class TestCreateInstantPayoutUtils:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        self.payment_account_id = 123
        self.amount = 200
        self.create_instant_payout_operation = CreateInstantPayout(
            stripe_payout_request_repo=stripe_payout_request_repo,
            payment_account_repo=payment_account_repo,
            stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
            stripe_async_client=stripe_async_client,
            logger=mocker.Mock(),
            request=CreateInstantPayoutRequest(
                payout_account_id=self.payment_account_id,
                amount=self.amount,
                payout_type=PayoutType.INSTANT,
            ),
        )

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def stripe_payout_request_repo(
        self, payout_bankdb: DB
    ) -> StripePayoutRequestRepository:
        return StripePayoutRequestRepository(database=payout_bankdb)

    @pytest.fixture
    def stripe_managed_account_transfer_repo(
        self, payout_bankdb: DB
    ) -> StripeManagedAccountTransferRepository:
        return StripeManagedAccountTransferRepository(database=payout_bankdb)

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

    async def test_create_sma_transfer_with_amount_success(
        self, payment_account_repo: PaymentAccountRepository
    ):
        # prepare Stripe Managed Account and insert, then validate
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # create sma transfer and validate
        sma_transfer = await self.create_instant_payout_operation.create_sma_transfer_with_amount(
            stripe_managed_account=sma, amount=self.amount
        )

        assert sma_transfer
        assert sma_transfer.amount == self.amount
        assert sma_transfer.to_stripe_account_id == sma.stripe_id

    async def test_create_instant_payout_without_payment_account(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
        @asyncio.coroutine
        def mock_get_payment_account(*args, **kwargs):
            return None

        mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_payment_account_by_id",
            side_effect=mock_get_payment_account,
        )
        with pytest.raises(PayoutError) as e:
            await self.create_instant_payout_operation._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID.value
            ]
        )

    async def test_create_instant_payout_without_sma(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
    ):
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )

        @asyncio.coroutine
        def mock_get_payment_account(*args, **kwargs):
            return payment_account

        @asyncio.coroutine
        def mock_get_sma(*args, **kwargs):
            return None

        mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_stripe_managed_account_by_id",
            side_effect=mock_get_sma,
        )
        mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_payment_account_by_id",
            side_effect=mock_get_payment_account,
        )

        with pytest.raises(PayoutError) as e:
            await self.create_instant_payout_operation._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_MANAGED_ACCOUNT
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_STRIPE_MANAGED_ACCOUNT.value
            ]
        )

    async def test_create_stripe_transfer_success(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
        # prepare Stripe Managed Account and insert, then validate
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # create sma transfer and validate
        sma_transfer = await self.create_instant_payout_operation.create_sma_transfer_with_amount(
            stripe_managed_account=sma, amount=self.amount
        )
        assert sma_transfer

        stripe_transfer_id = "acct_test_stripe_transfer"
        reversals = Transfer.Reversals(
            object="list",
            data=[],
            has_more=False,
            total_count=0,
            url="/v1/transfers/tr_1FJrsxBKMMeR8JVH7C4vtauG/reversals",
        )
        stripe_transfer = Transfer(
            id=stripe_transfer_id,
            object="transfer",
            amount=100,
            amount_reversed=0,
            balance_transaction="txn_1F3zLCBKMMeR8JVHehTbTzGO",
            created=1568768340,
            currency="aud",
            description="null",
            destination="acct_1EVmnIBKMMeR8JVH",
            destination_payment="py_FpWY3tDkEm64RD",
            livemode=False,
            metadata={},
            reversals=reversals,
            reversed=False,
            source_transaction="null",
            source_type="card",
            transfer_group="null",
        )

        @asyncio.coroutine
        def mock_create_transfer(*args, **kwargs):
            return stripe_transfer

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_transfer",
            side_effect=mock_create_transfer,
        )

        response = await self.create_instant_payout_operation.create_stripe_transfer(
            stripe_managed_account=sma, sma_transfer=sma_transfer
        )

        assert response
