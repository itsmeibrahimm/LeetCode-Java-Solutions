import asyncio
import uuid

import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.config.app_config import AppConfig
from app.commons.database.infra import DB
from app.commons.providers.stripe.stripe_client import StripeAsyncClient, StripeClient
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import StripeClientSettings
from app.commons.utils.pool import ThreadPoolHelper
from app.payout.core.account.processors.cancel_payout import (
    CancelPayout,
    CancelPayoutRequest,
)
from app.payout.core.exceptions import (
    PayoutError,
    PayoutErrorCode,
    payout_error_message_maps,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_stripe_transfer,
    prepare_and_insert_transfer,
    mock_payout,
    prepare_and_insert_payment_account,
)


class TestCancelPayout:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe: StripeAsyncClient,
    ):
        self.cancel_payout_op = CancelPayout(
            stripe_transfer_repo=stripe_transfer_repo,
            payment_account_repo=payment_account_repo,
            logger=mocker.Mock(),
            stripe=stripe,
            request=CancelPayoutRequest(transfer_id="1234", payout_account_id="1234"),
        )

    @pytest.fixture
    def stripe_transfer_repo(self, payout_maindb: DB) -> StripeTransferRepository:
        return StripeTransferRepository(database=payout_maindb)

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture()
    def stripe(self, app_config: AppConfig):
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

    async def test_cancel_payout_processor_invalid_payment_account(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe: StripeAsyncClient,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        request = CancelPayoutRequest(
            transfer_id=str(transfer.id), payout_account_id=-1
        )
        cancel_payout_op = CancelPayout(
            request=request,
            stripe_transfer_repo=stripe_transfer_repo,
            payment_account_repo=payment_account_repo,
            stripe=stripe,
            logger=mocker.Mock(),
        )

        with pytest.raises(PayoutError) as e:
            await cancel_payout_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_PAYMENT_ACCOUNT_ID
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_PAYMENT_ACCOUNT_ID.value
            ]
        )

    async def test_cancel_payout_processor_invalid_stripe_transfer(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe: StripeAsyncClient,
    ):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        request = CancelPayoutRequest(
            transfer_id="-1", payout_account_id=payment_account.id
        )
        cancel_payout_op = CancelPayout(
            request=request,
            stripe_transfer_repo=stripe_transfer_repo,
            payment_account_repo=payment_account_repo,
            stripe=stripe,
            logger=mocker.Mock(),
        )
        with pytest.raises(PayoutError) as e:
            await cancel_payout_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.INVALID_STRIPE_ACCOUNT.value]
        )

    async def test_cancel_payout_processor_success(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe: StripeAsyncClient,
    ):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )

        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )

        mocked_cancelled_payout = mock_payout(status="canceled")

        @asyncio.coroutine
        def mock_cancel_payout(*args, **kwargs):
            return mocked_cancelled_payout

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.cancel_payout",
            side_effect=mock_cancel_payout,
        )

        request = CancelPayoutRequest(
            transfer_id=str(transfer.id), payout_account_id=payment_account.id
        )
        cancel_payout_op = CancelPayout(
            request=request,
            stripe_transfer_repo=stripe_transfer_repo,
            payment_account_repo=payment_account_repo,
            stripe=stripe,
            logger=mocker.Mock(),
        )
        await cancel_payout_op._execute()
        retrieved_stripe_transfer = await stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id
        )
        assert retrieved_stripe_transfer
        assert retrieved_stripe_transfer.stripe_status == mocked_cancelled_payout.status

    async def test_cancel_stripe_transfer_invalid_stripe_status_raise_exception(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )

        mocked_payout = mock_payout(status="paid")

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )

        with pytest.raises(PayoutError) as e:
            await self.cancel_payout_op.cancel_stripe_transfer(
                stripe_transfer=stripe_transfer, payment_account=payment_account
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_PAYOUT
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.INVALID_STRIPE_PAYOUT.value]
        )

    async def test_cancel_stripe_transfer_no_transfer_of_stripe_found(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
            stripe_status="pending",
        )

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return None

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )
        assert not await self.cancel_payout_op.cancel_stripe_transfer(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )

    async def test_cancel_stripe_transfer_success(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )

        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )

        mocked_cancelled_payout = mock_payout(status="canceled")

        @asyncio.coroutine
        def mock_cancel_payout(*args, **kwargs):
            return mocked_cancelled_payout

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.cancel_payout",
            side_effect=mock_cancel_payout,
        )
        await self.cancel_payout_op.cancel_stripe_transfer(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )

        retrieved_stripe_transfer = await stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id
        )
        assert retrieved_stripe_transfer
        assert retrieved_stripe_transfer.stripe_status == mocked_cancelled_payout.status

    async def test_sync_stripe_status_no_stripe_transfer(
        self,
        stripe_transfer_repo: StripeTransferRepository,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo, transfer_id=transfer.id
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )

        synced_stripe_transfer, payout = await self.cancel_payout_op.sync_stripe_status(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )
        assert not payout

    async def test_sync_stripe_status_success(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )

        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )
        await self.cancel_payout_op.sync_stripe_status(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )

        retrieved_stripe_transfer = await stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id
        )
        assert retrieved_stripe_transfer
        assert retrieved_stripe_transfer.stripe_status == mocked_payout.status

    async def test_get_stripe_transfer_no_stripe_id(
        self,
        stripe_transfer_repo: StripeTransferRepository,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo, transfer_id=transfer.id
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )

        assert not await self.cancel_payout_op.get_stripe_transfer(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )

    async def test_get_stripe_transfer_success(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )

        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )

        payout = await self.cancel_payout_op.get_stripe_transfer(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )
        assert payout == mocked_payout
