import uuid
from datetime import datetime, timezone

import pytest

from app.commons.database.infra import DB
from app.payout.repository.maindb.model.stripe_transfer import (
    StripeTransferCreate,
    StripeTransferUpdate,
)
from app.payout.repository.maindb.model.transfer import TransferCreate, TransferUpdate
from app.payout.repository.maindb.transfer import TransferRepository
from app.testcase_utils import validate_expected_items_in_dict


class TestTransferRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    async def test_create_update_get_transfer(self, transfer_repo: TransferRepository):
        data = TransferCreate(
            subtotal=123,
            adjustments="some-adjustment",
            amount=123,
            method="stripe",
            currency="currency",
            submitted_at=datetime.now(timezone.utc),
            deleted_at=datetime.now(timezone.utc),
            manual_transfer_reason="manual_transfer_reason",
            status="status",
            status_code="status_code",
            submitting_at=datetime.now(timezone.utc),
            should_retry_on_failure=True,
            statement_description="statement_description",
            created_by_id=123,
            deleted_by_id=321,
            payment_account_id=123,
            recipient_id=321,
            recipient_ct_id=123,
            submitted_by_id=321,
        )

        assert len(data.__fields_set__) == len(
            data.__fields__
        ), "all fields should be set"

        created = await transfer_repo.create_transfer(data)
        assert created.id, "account is created, assigned an ID"

        validate_expected_items_in_dict(
            expected=data.dict(skip_defaults=True), actual=created.dict()
        )

        assert created == await transfer_repo.get_transfer_by_id(
            created.id
        ), "retrieved account matches"

        update_data = TransferUpdate(
            subtotal=123, adjustments="some-adjustment", amount=123, method="stripe"
        )

        updated = await transfer_repo.update_transfer_by_id(
            transfer_id=created.id, data=update_data
        )

        assert updated
        validate_expected_items_in_dict(
            expected=update_data.dict(skip_defaults=True), actual=updated.dict()
        )

    async def test_get_transfer_by_id_not_found(self, transfer_repo):
        assert not await transfer_repo.get_transfer_by_id(transfer_id=-1)

    async def test_update_transfer_by_id_not_found(self, transfer_repo):
        assert not await transfer_repo.update_transfer_by_id(
            transfer_id=-1, data=TransferUpdate(subtotal=100)
        )

    async def test_create_update_get_delete_stripe_transfer(self, transfer_repo):
        existing_transfer = await transfer_repo.create_transfer(
            TransferCreate(
                subtotal=123, adjustments="some-adjustment", amount=123, method="stripe"
            )
        )

        data = StripeTransferCreate(
            stripe_status="status",
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

        created = await transfer_repo.create_stripe_transfer(data)
        assert created.id, "account is created, assigned an ID"

        validate_expected_items_in_dict(
            expected=data.dict(skip_defaults=True), actual=created.dict()
        )

        assert created == await transfer_repo.get_stripe_transfer_by_id(
            created.id
        ), "retrieved account matches"

        assert created == await transfer_repo.get_stripe_transfer_by_stripe_id(
            stripe_id=created.stripe_id
        )

        assert created in await transfer_repo.get_stripe_transfers_by_transfer_id(
            transfer_id=created.transfer_id
        )

        update_data = StripeTransferUpdate(stripe_status="new_status")

        updated = await transfer_repo.update_stripe_transfer_by_id(
            stripe_transfer_id=created.id, data=update_data
        )

        assert updated
        validate_expected_items_in_dict(
            expected=update_data.dict(skip_defaults=True), actual=updated.dict()
        )

        deleted_count = await transfer_repo.delete_stripe_transfer_by_stripe_id(
            stripe_id=updated.stripe_id
        )

        assert (
            deleted_count == 1
        ), "should be exactly one deleted"  # stripe_id was unique'd by uuid

        assert not await transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=updated.transfer_id
        )

    async def test_get_stripe_transfer_by_id_not_found(self, transfer_repo):
        assert not await transfer_repo.get_stripe_transfer_by_id(stripe_transfer_id=-1)

    async def test_get_stripe_transfer_by_stripe_id_not_found(self, transfer_repo):
        assert not await transfer_repo.get_stripe_transfer_by_stripe_id(
            stripe_id="heregoesnothing"
        )

    async def test_get_stripe_transfer_by_transfer_id_not_found(self, transfer_repo):
        empty = await transfer_repo.get_stripe_transfers_by_transfer_id(transfer_id=-1)
        assert len(empty) == 0

    async def test_update_stripe_transfer_by_id_not_found(self, transfer_repo):
        assert not await transfer_repo.update_stripe_transfer_by_id(
            stripe_transfer_id=-1, data=StripeTransferUpdate(stripe_status="st")
        )

    async def test_delete_stripe_transfer_by_stripe_id_not_found(self, transfer_repo):
        assert 0 == await transfer_repo.delete_stripe_transfer_by_stripe_id(
            stripe_id="heregoesnothing"
        )
