from datetime import datetime, timezone

import pytest

from app.commons.database.infra import DB
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepository,
)
from app.payout.repository.maindb.model.managed_account_transfer import (
    ManagedAccountTransferCreate,
    ManagedAccountTransferUpdate,
)
from app.payout.repository.maindb.model.transfer import TransferCreate
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.types import ManagedAccountTransferStatus


class TestTransferRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def managed_account_transfer_repo(
        self, payout_maindb: DB
    ) -> ManagedAccountTransferRepository:
        return ManagedAccountTransferRepository(database=payout_maindb)

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    async def test_create_managed_account_transfer_success(
        self,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
    ):
        payment_account_id = 12345678
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
            payment_account_id=payment_account_id,
            recipient_id=321,
            recipient_ct_id=123,
            submitted_by_id=321,
        )

        assert len(data.__fields_set__) == len(
            data.__fields__
        ), "all fields should be set"

        transfer = await transfer_repo.create_transfer(data)
        assert transfer.id, "transfer is created, assigned an ID"

        ma_transfer_data = ManagedAccountTransferCreate(
            amount=2000,
            transfer_id=transfer.id,
            payment_account_id=payment_account_id,
            currency="usd",
        )
        ma_transfer = await managed_account_transfer_repo.create_managed_account_transfer(
            ma_transfer_data
        )
        assert ma_transfer.id, "managed_account_transfer is created, assigned an ID"
        assert ma_transfer.stripe_id == ""
        assert ma_transfer.stripe_status == ""

    async def test_get_managed_account_transfer_by_id_success(
        self,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
    ):
        payment_account_id = 12345678
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
            payment_account_id=payment_account_id,
            recipient_id=321,
            recipient_ct_id=123,
            submitted_by_id=321,
        )

        assert len(data.__fields_set__) == len(
            data.__fields__
        ), "all fields should be set"

        transfer = await transfer_repo.create_transfer(data)
        assert transfer.id, "transfer is created, assigned an ID"

        ma_transfer_data = ManagedAccountTransferCreate(
            amount=2000,
            transfer_id=transfer.id,
            payment_account_id=payment_account_id,
            currency="usd",
        )
        ma_transfer = await managed_account_transfer_repo.create_managed_account_transfer(
            ma_transfer_data
        )
        assert ma_transfer.id, "managed_account_transfer is created, assigned an ID"
        assert ma_transfer.stripe_id == ""
        assert ma_transfer.stripe_status == ""

        retrieved_ma_transfer = await managed_account_transfer_repo.get_managed_account_transfer_by_id(
            ma_transfer.id
        )
        assert (
            retrieved_ma_transfer == ma_transfer
        ), "retrieved managed account transfer matches"

    async def test_update_managed_account_transfer_by_id_success(
        self,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
    ):
        payment_account_id = 12345678
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
            payment_account_id=payment_account_id,
            recipient_id=321,
            recipient_ct_id=123,
            submitted_by_id=321,
        )

        assert len(data.__fields_set__) == len(
            data.__fields__
        ), "all fields should be set"

        transfer = await transfer_repo.create_transfer(data)
        assert transfer.id, "transfer is created, assigned an ID"

        ma_transfer_data = ManagedAccountTransferCreate(
            amount=2000,
            transfer_id=transfer.id,
            payment_account_id=payment_account_id,
            currency="usd",
        )
        ma_transfer = await managed_account_transfer_repo.create_managed_account_transfer(
            ma_transfer_data
        )
        assert ma_transfer.id, "managed_account_transfer is created, assigned an ID"
        assert ma_transfer.stripe_id == ""
        assert ma_transfer.stripe_status == ""

        timestamp = datetime.now(timezone.utc)
        update_request = ManagedAccountTransferUpdate(
            amount=4000,
            stripe_id="updated_test_stripe_id",
            stripe_status=ManagedAccountTransferStatus.PAID.value,
            submitted_at=timestamp,
        )
        updated_ma_transfer = await managed_account_transfer_repo.update_managed_account_transfer_by_id(
            ma_transfer.id, update_request
        )
        assert updated_ma_transfer
        assert updated_ma_transfer.id == ma_transfer.id
        assert updated_ma_transfer.amount == 4000
        assert updated_ma_transfer.stripe_id == "updated_test_stripe_id"
        assert (
            updated_ma_transfer.stripe_status == ManagedAccountTransferStatus.PAID.value
        )
        assert updated_ma_transfer.submitted_at == timestamp

    async def test_get_ma_transfer_by_id_not_found(
        self, managed_account_transfer_repo: ManagedAccountTransferRepository
    ):
        assert not await managed_account_transfer_repo.get_managed_account_transfer_by_id(
            managed_account_transfer_id=-1
        )

    async def test_update_ma_transfer_by_id_not_found(
        self, managed_account_transfer_repo: ManagedAccountTransferRepository
    ):
        assert not await managed_account_transfer_repo.update_managed_account_transfer_by_id(
            managed_account_transfer_id=-1,
            data=ManagedAccountTransferUpdate(amount=200),
        )
