import uuid
import pytest

from app.commons.database.infra import DB
from app.payout.repository.maindb.model.stripe_transfer import StripeTransferUpdate
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_stripe_transfer,
    prepare_and_insert_transfer,
)
from app.payout.models import StripePayoutStatus


class TestTransferRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    @pytest.fixture
    def stripe_transfer_repo(self, payout_maindb: DB) -> StripeTransferRepository:
        return StripeTransferRepository(database=payout_maindb)

    async def test_create_stripe_transfer(
        self,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)

        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )

    async def test_get_stripe_transfer_by_id_and_stripe_id(
        self,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)

        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )
        assert stripe_transfer == await stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer.id
        ), "retrieved stripe_transfer matches"

        assert (
            stripe_transfer
            == await stripe_transfer_repo.get_stripe_transfer_by_stripe_id(
                stripe_id=stripe_transfer.stripe_id
            )
        ), "retrieved stripe_transfer matches"

    async def test_update_stripe_transfer(
        self,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo, transfer_id=transfer.id
        )

        updated_stripe_id = str(uuid.uuid4())
        update_request = StripeTransferUpdate(
            stripe_id=updated_stripe_id, stripe_status=StripePayoutStatus.FAILED.value
        )
        updated_stripe_transfer = await stripe_transfer_repo.update_stripe_transfer_by_id(
            stripe_transfer.id, update_request
        )
        assert updated_stripe_transfer
        assert updated_stripe_transfer.id == stripe_transfer.id
        assert updated_stripe_transfer.stripe_id == updated_stripe_id
        assert updated_stripe_transfer.stripe_status == StripePayoutStatus.FAILED.value

    async def test_delete_stripe_transfer(
        self,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )
        deleted_count = await stripe_transfer_repo.delete_stripe_transfer_by_stripe_id(
            stripe_id=stripe_transfer.stripe_id
        )
        assert (
            deleted_count == 1
        ), "should be exactly one deleted"  # stripe_id was unique'd by uuid
        assert not await stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id
        )

    async def test_get_all_and_latest_stripe_transfer_by_transfer_id(
        self,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo, transfer_id=transfer.id
        )
        second_stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo, transfer_id=transfer.id
        )

        retrieved_stripe_transfers = await stripe_transfer_repo.get_stripe_transfers_by_transfer_id(
            transfer_id=transfer.id
        )
        assert len(retrieved_stripe_transfers) == 2
        assert stripe_transfer in retrieved_stripe_transfers
        assert second_stripe_transfer in retrieved_stripe_transfers
        assert (
            second_stripe_transfer
            == await stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
                transfer_id=transfer.id
            )
        )

    async def test_get_all_ongoing_stripe_transfers_by_transfer_id(
        self,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
    ):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo, transfer_id=transfer.id
        )
        second_stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status=StripePayoutStatus.FAILED.value,
        )

        ongoing_stripe_transfers = await stripe_transfer_repo.get_all_ongoing_stripe_transfers_by_transfer_id(
            transfer_id=transfer.id
        )
        assert len(ongoing_stripe_transfers) == 1
        assert stripe_transfer in ongoing_stripe_transfers
        assert second_stripe_transfer not in ongoing_stripe_transfers

    async def test_get_stripe_transfer_by_id_not_found(self, stripe_transfer_repo):
        assert not await stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=-1
        )

    async def test_get_stripe_transfer_by_stripe_id_not_found(
        self, stripe_transfer_repo
    ):
        assert not await stripe_transfer_repo.get_stripe_transfer_by_stripe_id(
            stripe_id="heregoesnothing"
        )

    async def test_get_stripe_transfer_by_transfer_id_not_found(
        self, stripe_transfer_repo
    ):
        empty = await stripe_transfer_repo.get_stripe_transfers_by_transfer_id(
            transfer_id=-1
        )
        assert len(empty) == 0

    async def test_update_stripe_transfer_by_id_not_found(self, stripe_transfer_repo):
        assert not await stripe_transfer_repo.update_stripe_transfer_by_id(
            stripe_transfer_id=-1,
            data=StripeTransferUpdate(stripe_status=StripePayoutStatus.PENDING.value),
        )

    async def test_delete_stripe_transfer_by_stripe_id_not_found(
        self, stripe_transfer_repo
    ):
        assert 0 == await stripe_transfer_repo.delete_stripe_transfer_by_stripe_id(
            stripe_id="heregoesnothing"
        )
