import pytest
import pytest_mock

from app.commons.context.app_context import AppContext
from app.payout.core.transfer.processors.monitor_creating_status_transfer import (
    MonitorCreatingStatusTransfer,
    MonitorCreatingStatusTransferRequest,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.model.transfer import TransferStatus
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_transfer,
    prepare_and_insert_payment_account,
    prepare_and_insert_transaction,
)


class TestMonitorCreatingStatusTransfer:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        app_context: AppContext,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        transaction_repo: TransactionRepository,
    ):
        self.transfer_repo = transfer_repo
        self.transaction_repo = transaction_repo
        self.payment_account_repo = payment_account_repo
        self.mocker = mocker
        self.kafka_producer = app_context.kafka_producer

    async def test_execute_monitor_creating_status_transfer_amount_not_match(self):
        # not update transfer if the amount mismatch
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            amount=100,
            payment_account_id=payment_account.id,
            status="creating",
        )
        await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo,
            amount=200,
            payout_account_id=payment_account.id,
            transfer_id=transfer.id,
        )
        monitor_op = MonitorCreatingStatusTransfer(
            request=MonitorCreatingStatusTransferRequest(transfer_ids=[transfer.id]),
            kafka_producer=self.kafka_producer,
            transaction_repo=self.transaction_repo,
            transfer_repo=self.transfer_repo,
        )
        await monitor_op._execute()
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer == transfer

    async def test_execute_monitor_creating_status_transfers_success(self):
        # prepare one transfer with no txn attached and one normal transfer, should be updated to NEW and DELETED
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer_without_txn = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            payment_account_id=payment_account.id,
            status="creating",
        )
        transfer_with_txn = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            payment_account_id=payment_account.id,
            status="creating",
        )
        await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo,
            amount=transfer_with_txn.amount,
            payout_account_id=payment_account.id,
            transfer_id=transfer_with_txn.id,
        )
        monitor_op = MonitorCreatingStatusTransfer(
            request=MonitorCreatingStatusTransferRequest(
                transfer_ids=[transfer_with_txn.id, transfer_without_txn.id]
            ),
            kafka_producer=self.kafka_producer,
            transaction_repo=self.transaction_repo,
            transfer_repo=self.transfer_repo,
        )
        await monitor_op._execute()
        retrieved_transfer_with_txn = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer_with_txn.id
        )
        assert retrieved_transfer_with_txn
        assert retrieved_transfer_with_txn.status == TransferStatus.NEW
        retrieved_transfer_without_txn = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer_without_txn.id
        )
        assert retrieved_transfer_without_txn
        assert retrieved_transfer_without_txn.status == TransferStatus.DELETED
