from datetime import datetime, timezone, timedelta

import pytest

from app.commons.database.infra import DB
from app.payout.repository.maindb.model.transfer import TransferUpdate, TransferStatus
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import prepare_and_insert_transfer
from app.testcase_utils import validate_expected_items_in_dict


class TestTransferRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    @pytest.fixture
    def stripe_transfer_repo(self, payout_maindb: DB) -> StripeTransferRepository:
        return StripeTransferRepository(database=payout_maindb)

    async def test_create_transfer(self, transfer_repo: TransferRepository):
        await prepare_and_insert_transfer(transfer_repo=transfer_repo)

    async def test_get_transfer(self, transfer_repo: TransferRepository):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        assert transfer == await transfer_repo.get_transfer_by_id(
            transfer.id
        ), "retrieved transfer matches"

    async def test_update_transfer(self, transfer_repo: TransferRepository):
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        update_data = TransferUpdate(
            subtotal=123, adjustments="some-adjustment", amount=123, method="stripe"
        )
        updated = await transfer_repo.update_transfer_by_id(
            transfer_id=transfer.id, data=update_data
        )

        assert updated
        validate_expected_items_in_dict(
            expected=update_data.dict(skip_defaults=True), actual=updated.dict()
        )

    async def test_get_transfer_by_id_not_found(self, transfer_repo):
        assert not await transfer_repo.get_transfer_by_id(transfer_id=-1)

    async def test_get_transfers_by_ids(self, transfer_repo):
        transfer_a = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        transfer_b = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        transfer_c = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        transfer_ids = [transfer_a.id, transfer_b.id]
        retrieved_transfers = await transfer_repo.get_transfers_by_ids(
            transfer_ids=transfer_ids
        )
        assert len(retrieved_transfers) == 2
        assert transfer_a in retrieved_transfers
        assert transfer_b in retrieved_transfers
        assert transfer_c not in retrieved_transfers

    async def test_get_transfers_by_submitted_at_and_method_not_found(
        self, transfer_repo
    ):
        transfers = await transfer_repo.get_transfers_by_submitted_at_and_method(
            start_time=datetime.now(timezone.utc)
        )
        assert len(transfers) == 0

    async def test_get_transfers_by_submitted_at_and_method_success(
        self, transfer_repo
    ):
        original_transfer_ids = await transfer_repo.get_transfers_by_submitted_at_and_method(
            start_time=datetime(2019, 8, 10, tzinfo=timezone.utc)
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, submitted_at=datetime.now(timezone.utc)
        )
        new_transfer_ids = await transfer_repo.get_transfers_by_submitted_at_and_method(
            start_time=datetime(2019, 8, 10, tzinfo=timezone.utc)
        )
        assert len(new_transfer_ids) - len(original_transfer_ids) == 1
        diff = list(set(new_transfer_ids) - set(original_transfer_ids))
        assert diff[0] == transfer.id

    async def test_get_unsubmitted_transfer_ids_not_found(self, transfer_repo):
        timestamp = datetime.now(timezone.utc) + timedelta(days=1)
        original_transfer_ids = await transfer_repo.get_unsubmitted_transfer_ids(
            created_before=timestamp
        )
        new_transfer_ids = await transfer_repo.get_unsubmitted_transfer_ids(
            created_before=timestamp
        )
        assert len(new_transfer_ids) == len(original_transfer_ids)

    async def test_get_unsubmitted_transfer_ids_success(self, transfer_repo):
        timestamp = datetime.now(timezone.utc) + timedelta(days=1)
        original_transfer_ids = await transfer_repo.get_unsubmitted_transfer_ids(
            created_before=timestamp
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, status=TransferStatus.NEW
        )
        new_transfer_ids = await transfer_repo.get_unsubmitted_transfer_ids(
            created_before=timestamp
        )
        assert len(new_transfer_ids) - len(original_transfer_ids) == 1
        assert (
            list(set(new_transfer_ids) - set(original_transfer_ids))[0] == transfer.id
        )

    async def test_update_transfer_by_id_not_found(self, transfer_repo):
        assert not await transfer_repo.update_transfer_by_id(
            transfer_id=-1, data=TransferUpdate(subtotal=100)
        )
