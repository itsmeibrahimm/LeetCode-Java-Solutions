import asyncio
import uuid

import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.core.transfer.cancel_payout import CancelPayout, CancelPayoutRequest
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
        transfer_repo: TransferRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        self.cancel_payout_op = CancelPayout(
            stripe_transfer_repo=stripe_transfer_repo,
            payment_account_repo=payment_account_repo,
            logger=mocker.Mock(),
            stripe=stripe_async_client,
            request=CancelPayoutRequest(transfer_id="1234", payout_account_id="1234"),
        )
        self.stripe_transfer_repo = stripe_transfer_repo
        self.payment_account_repo = payment_account_repo
        self.transfer_repo = transfer_repo
        self.stripe = stripe_async_client
        self.mocker = mocker

    async def test_cancel_payout_processor_invalid_payment_account(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        request = CancelPayoutRequest(
            transfer_id=str(transfer.id), payout_account_id=-1
        )
        cancel_payout_op = CancelPayout(
            request=request,
            stripe_transfer_repo=self.stripe_transfer_repo,
            payment_account_repo=self.payment_account_repo,
            stripe=self.stripe,
            logger=self.mocker.Mock(),
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

    async def test_cancel_payout_processor_invalid_stripe_transfer(self):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        request = CancelPayoutRequest(
            transfer_id="-1", payout_account_id=payment_account.id
        )
        cancel_payout_op = CancelPayout(
            request=request,
            stripe_transfer_repo=self.stripe_transfer_repo,
            payment_account_repo=self.payment_account_repo,
            stripe=self.stripe,
            logger=self.mocker.Mock(),
        )
        await cancel_payout_op._execute()

    async def test_cancel_payout_processor_success(self):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )

        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )

        mocked_cancelled_payout = mock_payout(status="canceled")

        @asyncio.coroutine
        def mock_cancel_payout(*args, **kwargs):
            return mocked_cancelled_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.cancel_payout",
            side_effect=mock_cancel_payout,
        )

        request = CancelPayoutRequest(
            transfer_id=str(transfer.id), payout_account_id=payment_account.id
        )
        cancel_payout_op = CancelPayout(
            request=request,
            stripe_transfer_repo=self.stripe_transfer_repo,
            payment_account_repo=self.payment_account_repo,
            stripe=self.stripe,
            logger=self.mocker.Mock(),
        )
        await cancel_payout_op._execute()
        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id
        )
        assert retrieved_stripe_transfer
        assert retrieved_stripe_transfer.stripe_status == mocked_cancelled_payout.status

    async def test_cancel_stripe_transfer_invalid_stripe_status_raise_exception(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )

        mocked_payout = mock_payout(status="paid")

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
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

    async def test_cancel_stripe_transfer_no_transfer_of_stripe_found(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
            stripe_status="pending",
        )

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return None

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )
        assert not await self.cancel_payout_op.cancel_stripe_transfer(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )

    async def test_cancel_stripe_transfer_success(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )

        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )

        mocked_cancelled_payout = mock_payout(status="canceled")

        @asyncio.coroutine
        def mock_cancel_payout(*args, **kwargs):
            return mocked_cancelled_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.cancel_payout",
            side_effect=mock_cancel_payout,
        )
        await self.cancel_payout_op.cancel_stripe_transfer(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )

        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id
        )
        assert retrieved_stripe_transfer
        assert retrieved_stripe_transfer.stripe_status == mocked_cancelled_payout.status

    async def test_sync_stripe_status_no_stripe_transfer(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer.id
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )

        synced_stripe_transfer, payout = await self.cancel_payout_op.sync_stripe_status(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )
        assert not payout

    async def test_sync_stripe_status_success(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )

        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )
        await self.cancel_payout_op.sync_stripe_status(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )

        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id
        )
        assert retrieved_stripe_transfer
        assert retrieved_stripe_transfer.stripe_status == mocked_payout.status

    async def test_get_stripe_transfer_no_stripe_id(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer.id
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )

        assert not await self.cancel_payout_op.get_stripe_transfer(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )

    async def test_get_stripe_transfer_success(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )

        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )

        payout = await self.cancel_payout_op.get_stripe_transfer(
            stripe_transfer=stripe_transfer, payment_account=payment_account
        )
        assert payout == mocked_payout
