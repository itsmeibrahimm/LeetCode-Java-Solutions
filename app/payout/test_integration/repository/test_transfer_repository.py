from datetime import datetime, timezone

import pytest

from app.commons.database.infra import DB
from app.payout.repository.maindb.model.transfer import TransferCreate, TransferUpdate
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.testcase_utils import validate_expected_items_in_dict


class TestTransferRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    @pytest.fixture
    def stripe_transfer_repo(self, payout_maindb: DB) -> StripeTransferRepository:
        return StripeTransferRepository(database=payout_maindb)

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
        assert created.id, "transfer is created, assigned an ID"

        validate_expected_items_in_dict(
            expected=data.dict(skip_defaults=True), actual=created.dict()
        )

        assert created == await transfer_repo.get_transfer_by_id(
            created.id
        ), "retrieved transfer matches"

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
