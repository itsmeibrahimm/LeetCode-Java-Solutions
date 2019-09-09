import uuid
from datetime import datetime, timezone

import pytest

from app.commons.database.infra import DB
from app.payout.repository.maindb.model.stripe_transfer import (
    StripeTransferCreate,
    StripeTransferUpdate,
)
from app.payout.repository.maindb.model.transfer import TransferCreate
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.types import StripePayoutStatus
from app.testcase_utils import validate_expected_items_in_dict


class TestTransferRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    @pytest.fixture
    def stripe_transfer_repo(self, payout_maindb: DB) -> StripeTransferRepository:
        return StripeTransferRepository(database=payout_maindb)

    async def test_create_update_get_delete_stripe_transfer(
        self, transfer_repo, stripe_transfer_repo
    ):
        existing_transfer = await transfer_repo.create_transfer(
            TransferCreate(
                subtotal=123, adjustments="some-adjustment", amount=123, method="stripe"
            )
        )

        data = StripeTransferCreate(
            stripe_status=StripePayoutStatus.New.value,
            transfer_id=existing_transfer.id,
            stripe_id=str(uuid.uuid4()),
            stripe_request_id="stripe_request_id",
            stripe_failure_code="stripe_failure_code",
            stripe_account_id="stripe_account_id",
            stripe_account_type="stripe_account_type",
            country_shortname="country_shortname",
            bank_last_four="bank_last_four",
            bank_name="bank_name",
            submission_error_code="submission_error_code",
            submission_error_type="submission_error_type",
            submission_status="submission_status",
            submitted_at=datetime.now(timezone.utc),
        )

        assert len(data.__fields_set__) == len(
            data.__fields__
        ), "all fields should be set"

        created = await stripe_transfer_repo.create_stripe_transfer(data)
        assert created.id, "stripe_transfer is created, assigned an ID"

        validate_expected_items_in_dict(
            expected=data.dict(skip_defaults=True), actual=created.dict()
        )

        assert created == await stripe_transfer_repo.get_stripe_transfer_by_id(
            created.id
        ), "retrieved stripe_transfer matches"

        assert created == await stripe_transfer_repo.get_stripe_transfer_by_stripe_id(
            stripe_id=created.stripe_id
        )

        data = StripeTransferCreate(
            stripe_status=StripePayoutStatus.Failed.value,
            transfer_id=existing_transfer.id,
            stripe_id=str(uuid.uuid4()),
            stripe_request_id="stripe_request_id",
            stripe_failure_code="stripe_failure_code",
            stripe_account_id="stripe_account_id",
            stripe_account_type="stripe_account_type",
            country_shortname="country_shortname",
            bank_last_four="bank_last_four",
            bank_name="bank_name",
            submission_error_code="submission_error_code",
            submission_error_type="submission_error_type",
            submission_status="submission_status",
            submitted_at=datetime.now(timezone.utc),
        )

        failed_stripe_transfer = await stripe_transfer_repo.create_stripe_transfer(data)
        assert failed_stripe_transfer.id, "stripe_transfer is created, assigned an ID"

        retrieved_stripe_transfers = await stripe_transfer_repo.get_stripe_transfers_by_transfer_id(
            transfer_id=created.transfer_id
        )
        assert len(retrieved_stripe_transfers) == 2

        assert created in retrieved_stripe_transfers
        assert failed_stripe_transfer in retrieved_stripe_transfers

        assert (
            failed_stripe_transfer
            == await stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
                transfer_id=existing_transfer.id
            )
        )

        ongoing_stripe_transfers = await stripe_transfer_repo.get_all_ongoing_stripe_transfers_by_transfer_id(
            transfer_id=existing_transfer.id
        )
        assert len(ongoing_stripe_transfers) == 1
        assert created in ongoing_stripe_transfers
        assert failed_stripe_transfer not in ongoing_stripe_transfers

        update_data = StripeTransferUpdate(stripe_status=StripePayoutStatus.New.value)

        updated = await stripe_transfer_repo.update_stripe_transfer_by_id(
            stripe_transfer_id=created.id, data=update_data
        )

        assert updated
        validate_expected_items_in_dict(
            expected=update_data.dict(skip_defaults=True), actual=updated.dict()
        )

        deleted_count = await stripe_transfer_repo.delete_stripe_transfer_by_stripe_id(
            stripe_id=updated.stripe_id
        )
        assert (
            deleted_count == 1
        ), "should be exactly one deleted"  # stripe_id was unique'd by uuid
        assert not await stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=updated.id
        )

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
            data=StripeTransferUpdate(stripe_status=StripePayoutStatus.Pending.value),
        )

    async def test_delete_stripe_transfer_by_stripe_id_not_found(
        self, stripe_transfer_repo
    ):
        assert 0 == await stripe_transfer_repo.delete_stripe_transfer_by_stripe_id(
            stripe_id="heregoesnothing"
        )
