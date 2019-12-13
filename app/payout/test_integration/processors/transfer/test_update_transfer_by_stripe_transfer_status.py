import asyncio

import pytest
import pytest_mock

from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.core.transfer.processors.update_transfer_by_stripe_transfer_status import (
    UpdateTransferByStripeTransferStatus,
    UpdateTransferByStripeTransferStatusRequest,
)
from app.payout.repository.maindb.model.transfer import (
    TransferStatus,
    TransferStatusCode,
)
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

    async def test_update_transfer_status_from_latest_submission_same_status(self):
        # prepare a transfer with status NEW
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.NEW
        )
        await self.update_transfer_by_stripe_transfer_status_op.update_transfer_status_from_latest_submission(
            transfer=transfer
        )
        # check transfer is not updated
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer == transfer

    async def test_update_transfer_status_from_latest_submission_method_non_stripe(
        self
    ):
        # prepare a transfer
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, method="invalid_stripe"
        )
        await self.update_transfer_by_stripe_transfer_status_op.update_transfer_status_from_latest_submission(
            transfer=transfer
        )
        # check transfer is updated with NEW status and None status_code
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.NEW
        assert not retrieved_transfer.status_code

    async def test_update_transfer_status_from_latest_submission_method_stripe_and_failed_updated_status(
        self
    ):
        # prepare a transfer and a failed stripe_transfer
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            stripe_status="failed",
            transfer_id=transfer.id,
        )
        await self.update_transfer_by_stripe_transfer_status_op.update_transfer_status_from_latest_submission(
            transfer=transfer
        )

        # check transfer is updated with FAILED status and ERROR_GATEWAY_ACCOUNT_SETUP status_code
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.FAILED
        assert (
            retrieved_transfer.status_code
            == TransferStatusCode.ERROR_GATEWAY_ACCOUNT_SETUP
        )

    async def test_get_stripe_transfer_no_stripe_id(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer.id
        )
        assert not await self.update_transfer_by_stripe_transfer_status_op.get_stripe_transfer(
            stripe_transfer=stripe_transfer
        )

    async def test_sync_stripe_status_no_transfer_of_stripe(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer.id
        )
        assert not await self.update_transfer_by_stripe_transfer_status_op.sync_stripe_status(
            stripe_transfer=stripe_transfer
        )

    async def test_sync_stripe_status_return_false(self):
        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )

        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="pending",
            stripe_id="po_test_id",
        )
        assert not await self.update_transfer_by_stripe_transfer_status_op.sync_stripe_status(
            stripe_transfer=stripe_transfer
        )
        # confirm that stripe_transfer stripe_status is not changed
        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id
        )
        assert retrieved_stripe_transfer
        assert retrieved_stripe_transfer.stripe_status == mocked_payout.status

    async def test_sync_stripe_status_return_true(self):
        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )

        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="in_transit",
            stripe_id="po_test_id",
        )
        assert await self.update_transfer_by_stripe_transfer_status_op.sync_stripe_status(
            stripe_transfer=stripe_transfer
        )
        # confirm that stripe_transfer stripe_status is updated
        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id
        )
        assert retrieved_stripe_transfer
        assert retrieved_stripe_transfer.stripe_status == mocked_payout.status

    async def test_execute_update_transfer_by_stripe_transfer_status_with_stripe_transfer_success(
        self
    ):
        # prepare transfer with stripe_transfer associated with it
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="pending",
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
        # transfer should be updated to PENDING status
        await update_transfer_by_stripe_transfer_status_op._execute()
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.PENDING

    async def test_execute_update_transfer_by_stripe_transfer_status_without_stripe_transfer_no_update(
        self
    ):
        # prepare transfer without corresponding stripe_transfer
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
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
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        # no updates excepted for transfer
        assert retrieved_transfer
        assert retrieved_transfer == transfer
