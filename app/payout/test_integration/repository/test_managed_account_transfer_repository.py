from datetime import datetime, timezone

import pytest

from app.commons.database.infra import DB
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepository,
)
from app.payout.repository.maindb.model.managed_account_transfer import (
    ManagedAccountTransferUpdate,
)
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_transfer,
    prepare_and_insert_managed_account_transfer,
)
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
        # prepare transfer and insert, then validate
        payment_account_id = 123456
        transfer = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, payment_account_id=payment_account_id
        )
        # prepare managed_account_transfer and insert, then validate content
        await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account_id,
            transfer_id=transfer.id,
        )

    async def test_get_managed_account_transfer_by_id_success(
        self,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
    ):
        # prepare transfer and insert, then validate
        payment_account_id = 123456
        transfer = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, payment_account_id=payment_account_id
        )

        # prepare managed_account_transfer and insert, then validate content
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account_id,
            transfer_id=transfer.id,
        )

        retrieved_ma_transfer = await managed_account_transfer_repo.get_managed_account_transfer_by_id(
            ma_transfer.id
        )
        assert (
            retrieved_ma_transfer == ma_transfer
        ), "retrieved managed account transfer matches"

    async def test_get_managed_account_transfer_by_transfer_id_success(
        self,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
    ):
        # prepare transfer and insert, then validate
        payment_account_id = 123456
        transfer = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, payment_account_id=payment_account_id
        )

        # prepare managed_account_transfer and insert, then validate content
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account_id,
            transfer_id=transfer.id,
        )
        retrieved_ma_transfer = await managed_account_transfer_repo.get_managed_account_transfer_by_transfer_id(
            transfer_id=transfer.id
        )
        assert (
            retrieved_ma_transfer == ma_transfer
        ), "retrieved managed account transfer matches"

    async def test_update_managed_account_transfer_by_id_success(
        self,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
    ):
        # prepare transfer and insert, then validate
        payment_account_id = 123456
        transfer = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, payment_account_id=payment_account_id
        )

        # prepare managed_account_transfer and insert, then validate content
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account_id,
            transfer_id=transfer.id,
        )

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

    async def test_get_ma_transfer_by_transfer_id_not_found(
        self, managed_account_transfer_repo: ManagedAccountTransferRepository
    ):
        assert not await managed_account_transfer_repo.get_managed_account_transfer_by_transfer_id(
            transfer_id=-1
        )

    async def test_update_ma_transfer_by_id_not_found(
        self, managed_account_transfer_repo: ManagedAccountTransferRepository
    ):
        assert not await managed_account_transfer_repo.update_managed_account_transfer_by_id(
            managed_account_transfer_id=-1,
            data=ManagedAccountTransferUpdate(amount=200),
        )
