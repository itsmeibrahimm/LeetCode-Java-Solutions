import asyncio
from datetime import datetime, timezone

import pytest
import pytest_mock

from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.core.transfer.processors.update_transfer_by_stripe_transfer_status import (
    UpdateTransferByStripeTransferStatus,
    UpdateTransferByStripeTransferStatusRequest,
)
from app.payout.models import TransferStatusCodeType
from app.payout.repository.maindb.model.transfer import TransferStatus
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_transfer,
    prepare_and_insert_stripe_transfer,
    mock_payout,
)


class TestUpdateTransferByStripeTransferStatus:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        self.update_transfer_by_stripe_transfer_status_op = UpdateTransferByStripeTransferStatus(
            transfer_repo=transfer_repo,
            stripe_transfer_repo=stripe_transfer_repo,
            logger=mocker.Mock(),
            stripe=stripe_async_client,
            request=UpdateTransferByStripeTransferStatusRequest(transfer_id=12345),
        )
        self.transfer_repo = transfer_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.mocker = mocker
        self.stripe = stripe_async_client

    async def test_execute_processor_with_synced_stripe_transfer_and_transfer_out_of_sync_success(
        self
    ):
        # transfer with in_transit status versus stripe_transfer and payout with status pending
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="pending",
            stripe_id=123,
        )
        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )

        update_transfer_by_stripe_transfer_status_op = UpdateTransferByStripeTransferStatus(
            transfer_repo=self.transfer_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
            logger=self.mocker.Mock(),
            stripe=self.stripe,
            request=UpdateTransferByStripeTransferStatusRequest(
                transfer_id=transfer.id
            ),
        )
        await update_transfer_by_stripe_transfer_status_op._execute()

        # stripe_transfer should not be updated
        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id
        )
        assert retrieved_stripe_transfer == stripe_transfer

        # transfer should be updated to PENDING status
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.PENDING

    async def test_execute_processor_with_no_stripe_id_no_update_on_transfer(self):
        # transfer with in_transit status versus stripe_transfer and payout with status pending
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.NEW
        )
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="pending",
        )
        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )

        update_transfer_by_stripe_transfer_status_op = UpdateTransferByStripeTransferStatus(
            transfer_repo=self.transfer_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
            logger=self.mocker.Mock(),
            stripe=self.stripe,
            request=UpdateTransferByStripeTransferStatusRequest(
                transfer_id=transfer.id
            ),
        )
        await update_transfer_by_stripe_transfer_status_op._execute()

        # stripe_transfer should not be updated since its status is sync with stripe payout
        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id
        )
        assert retrieved_stripe_transfer == stripe_transfer

        # transfer should remain as NEW
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.NEW

    async def test_execute_processor_with_synced_transfer_and_stripe_transfer(self):
        # transfer and stripe_transfer with synced status will not be updated
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status="pending"
        )
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="pending",
            stripe_id=123,
        )
        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )

        update_transfer_by_stripe_transfer_status_op = UpdateTransferByStripeTransferStatus(
            transfer_repo=self.transfer_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
            logger=self.mocker.Mock(),
            stripe=self.stripe,
            request=UpdateTransferByStripeTransferStatusRequest(
                transfer_id=transfer.id
            ),
        )
        await update_transfer_by_stripe_transfer_status_op._execute()

        # there will be no effects on stripe_transfer or transfer
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer == transfer

        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id
        )
        assert retrieved_stripe_transfer == stripe_transfer

    async def test_check_and_sync_stripe_transfer_status_no_stripe_id(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer.id
        )
        updated_stripe_transfer = await self.update_transfer_by_stripe_transfer_status_op.check_and_sync_stripe_transfer_status(
            stripe_transfer=stripe_transfer
        )
        assert not updated_stripe_transfer

    async def test_check_and_sync_stripe_transfer_status_synced_status_no_update(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="pending",
            stripe_id="some_random_stripe_id",
        )
        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )
        updated_stripe_transfer = await self.update_transfer_by_stripe_transfer_status_op.check_and_sync_stripe_transfer_status(
            stripe_transfer=stripe_transfer
        )
        assert stripe_transfer == updated_stripe_transfer

    async def test_check_and_sync_stripe_transfer_status_update_success(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id="some_random_stripe_id",
        )
        mocked_payout = mock_payout(status="in_transit")

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )
        updated_stripe_transfer = await self.update_transfer_by_stripe_transfer_status_op.check_and_sync_stripe_transfer_status(
            stripe_transfer=stripe_transfer
        )
        assert updated_stripe_transfer.id == stripe_transfer.id
        assert updated_stripe_transfer.stripe_status == mocked_payout.status

    async def test_check_and_sync_transfer_status_with_stripe_transfer_failed_stripe_transfer(
        self
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="failed",
        )
        updated_transfer = await self.update_transfer_by_stripe_transfer_status_op.check_and_sync_transfer_status_with_stripe_transfer(
            transfer=transfer, stripe_transfer=stripe_transfer
        )
        assert updated_transfer.status == TransferStatus.FAILED
        assert (
            updated_transfer.status_code
            == TransferStatusCodeType.ERROR_GATEWAY_ACCOUNT_SETUP
        )

    async def test_check_and_sync_transfer_status_with_stripe_transfer_update_success(
        self
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="pending",
        )
        updated_transfer = await self.update_transfer_by_stripe_transfer_status_op.check_and_sync_transfer_status_with_stripe_transfer(
            transfer=transfer, stripe_transfer=stripe_transfer
        )
        assert updated_transfer.status == TransferStatus.PENDING
        assert not updated_transfer.status_code

    async def test_check_and_sync_transfer_status_with_stripe_transfer_synced_status_no_update(
        self
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="in_transit",
        )
        updated_transfer = await self.update_transfer_by_stripe_transfer_status_op.check_and_sync_transfer_status_with_stripe_transfer(
            transfer=transfer, stripe_transfer=stripe_transfer
        )
        assert updated_transfer == transfer

    async def test_determine_transfer_status_with_stripe_transfer_transfer_deleted(
        self
    ):
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, deleted_at=datetime.now(timezone.utc)
        )
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer.id
        )
        status = self.update_transfer_by_stripe_transfer_status_op.determine_transfer_status_with_stripe_transfer(
            transfer=transfer, stripe_transfer=stripe_transfer
        )
        assert status == TransferStatus.DELETED

    async def test_determine_transfer_status_with_stripe_transfer_transfer_paid_zero_amount(
        self
    ):
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            amount=0,
            submitted_at=datetime.now(timezone.utc),
        )
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer.id
        )
        status = self.update_transfer_by_stripe_transfer_status_op.determine_transfer_status_with_stripe_transfer(
            transfer=transfer, stripe_transfer=stripe_transfer
        )
        assert status == TransferStatus.PAID

    async def test_determine_transfer_status_with_stripe_transfer_transfer_matches_stripe_transfer(
        self
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="in_transit",
        )
        status = self.update_transfer_by_stripe_transfer_status_op.determine_transfer_status_with_stripe_transfer(
            transfer=transfer, stripe_transfer=stripe_transfer
        )
        assert status == TransferStatus.IN_TRANSIT
