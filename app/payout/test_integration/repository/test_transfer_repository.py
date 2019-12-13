from datetime import datetime, timezone, timedelta

import pytest

from app.payout.repository.maindb.model.transfer import TransferUpdate, TransferStatus
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_transfer,
    prepare_and_insert_payment_account,
    prepare_and_insert_stripe_transfer,
)
from app.testcase_utils import validate_expected_items_in_dict


class TestTransferRepository:
    pytestmark = [pytest.mark.asyncio]

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

    async def test_get_transfers_by_payment_account_ids_and_count_not_found(
        self, transfer_repo
    ):
        transfers, count = await transfer_repo.get_transfers_by_payment_account_ids_and_count(
            payment_account_ids=[], offset=0, limit=10
        )
        assert len(transfers) == 0
        assert count == 0

    async def test_get_transfers_by_payment_account_ids_success(
        self, transfer_repo, payment_account_repo
    ):
        payment_account_a = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        payment_account_b = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )

        transfer_a = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, payment_account_id=payment_account_a.id
        )
        transfer_b = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, payment_account_id=payment_account_a.id
        )
        transfer_c = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, payment_account_id=payment_account_b.id
        )
        transfers, count = await transfer_repo.get_transfers_by_payment_account_ids_and_count(
            payment_account_ids=[payment_account_a.id], offset=0, limit=1
        )
        # due to limit, the return transfers list length should be 1
        # while the total number of transfers meet the requirements before limit should be 2
        # since the result is sorted by transfer id desc, the transfer inserted later should be returned
        assert len(transfers) == 1
        assert count == 2
        assert transfer_b in transfers
        assert transfer_a not in transfers
        assert transfer_c not in transfers

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

    async def test_get_positive_transfers_and_count_by_status_and_time_range(
        self, transfer_repo
    ):
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()
        original_transfers, original_count = await transfer_repo.get_transfers_and_count_by_status_and_time_range(
            status=TransferStatus.PENDING,
            offset=0,
            limit=50,
            has_positive_amount=True,
            start_time=start_time,
            end_time=end_time,
        )

        transfer_a = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, status=TransferStatus.PENDING
        )
        transfer_b = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, status=TransferStatus.PENDING, amount=-1
        )
        transfer_c = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, status=TransferStatus.FAILED
        )

        end_time = datetime.utcnow()
        new_transfers, new_count = await transfer_repo.get_transfers_and_count_by_status_and_time_range(
            status=TransferStatus.PENDING,
            offset=0,
            limit=50,
            has_positive_amount=True,
            start_time=start_time,
            end_time=end_time,
        )
        assert new_count - original_count == 1
        assert transfer_a not in original_transfers
        assert transfer_a in new_transfers
        assert transfer_b not in original_transfers
        assert transfer_b not in new_transfers
        assert transfer_c not in original_transfers
        assert transfer_c not in new_transfers

        transfer_d = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, status=TransferStatus.PENDING
        )

        transfers, count = await transfer_repo.get_transfers_and_count_by_status_and_time_range(
            status=TransferStatus.PENDING,
            offset=0,
            limit=50,
            has_positive_amount=True,
            start_time=start_time,
            end_time=end_time,
        )
        assert count - original_count == 1
        assert transfer_d not in original_transfers
        assert transfer_d not in transfers

    async def test_get_transfers_and_count_by_status_and_time_range(
        self, transfer_repo
    ):
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()
        original_transfers, original_count = await transfer_repo.get_transfers_and_count_by_status_and_time_range(
            status=TransferStatus.PENDING,
            offset=0,
            limit=50,
            has_positive_amount=False,
            start_time=start_time,
            end_time=end_time,
        )

        transfer_a = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, status=TransferStatus.PENDING
        )
        transfer_b = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, status=TransferStatus.PENDING, amount=-1
        )
        transfer_c = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, status=TransferStatus.FAILED
        )

        end_time = datetime.utcnow()
        new_transfers, new_count = await transfer_repo.get_transfers_and_count_by_status_and_time_range(
            status=TransferStatus.PENDING,
            offset=0,
            limit=50,
            has_positive_amount=False,
            start_time=start_time,
            end_time=end_time,
        )
        assert new_count - original_count == 2
        assert transfer_a not in original_transfers
        assert transfer_a in new_transfers
        assert transfer_b not in original_transfers
        assert transfer_b in new_transfers
        assert transfer_c not in original_transfers
        assert transfer_c not in new_transfers

        transfer_d = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, status=TransferStatus.PENDING
        )

        transfers, count = await transfer_repo.get_transfers_and_count_by_status_and_time_range(
            status=TransferStatus.PENDING,
            offset=0,
            limit=50,
            has_positive_amount=False,
            start_time=start_time,
            end_time=end_time,
        )
        assert count - original_count == 2
        assert transfer_d not in original_transfers
        assert transfer_d not in transfers

    async def test_get_positive_amount_transfers_and_count_by_time_range_not_submitted(
        self, transfer_repo, stripe_transfer_repo
    ):
        # negative amount transfers will not be filtered out
        # transfers with or without related stripe_transfers will be found while is_submitted flag is off
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()
        original_transfers, original_count = await transfer_repo.get_positive_amount_transfers_and_count_by_time_range(
            offset=0,
            limit=50,
            is_submitted=False,
            start_time=start_time,
            end_time=end_time,
        )

        transfer_a = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        transfer_b = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, amount=-1
        )
        transfer_c = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo, transfer_id=transfer_c.id
        )

        end_time = datetime.utcnow()
        new_transfers, new_count = await transfer_repo.get_positive_amount_transfers_and_count_by_time_range(
            offset=0,
            limit=50,
            is_submitted=False,
            start_time=start_time,
            end_time=end_time,
        )

        assert new_count - original_count == 2
        assert transfer_a not in original_transfers
        assert transfer_a in new_transfers
        assert transfer_b not in original_transfers
        assert transfer_b not in new_transfers
        assert transfer_c not in original_transfers
        assert transfer_c in new_transfers

    async def test_get_positive_amount_transfers_and_count_by_time_range_transfer_submitted(
        self, transfer_repo, stripe_transfer_repo
    ):
        # negative amount transfers will not be filtered out
        # only transfers with corresponding stripe_transfers will be found while is_submitted flag is on
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow()
        original_transfers, original_count = await transfer_repo.get_positive_amount_transfers_and_count_by_time_range(
            offset=0,
            limit=50,
            is_submitted=True,
            start_time=start_time,
            end_time=end_time,
        )

        transfer_a = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        transfer_b = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, amount=-1
        )
        transfer_c = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo, transfer_id=transfer_c.id
        )

        end_time = datetime.utcnow()
        new_transfers, new_count = await transfer_repo.get_positive_amount_transfers_and_count_by_time_range(
            offset=0,
            limit=50,
            is_submitted=True,
            start_time=start_time,
            end_time=end_time,
        )

        assert new_count - original_count == 1
        assert transfer_a not in original_transfers
        assert transfer_a not in new_transfers
        assert transfer_b not in original_transfers
        assert transfer_b not in new_transfers
        assert transfer_c not in original_transfers
        assert transfer_c in new_transfers

    async def test_update_transfer_by_id_not_found(self, transfer_repo):
        assert not await transfer_repo.update_transfer_by_id(
            transfer_id=-1, data=TransferUpdate(subtotal=100)
        )
