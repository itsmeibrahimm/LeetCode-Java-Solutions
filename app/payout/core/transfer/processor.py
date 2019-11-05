from aioredlock import Aioredlock
from structlog.stdlib import BoundLogger
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.core.transfer.processors.create_transfer import (
    CreateTransferRequest,
    CreateTransfer,
)
from app.payout.core.transfer.processors.submit_transfer import (
    SubmitTransferRequest,
    SubmitTransfer,
)
from app.payout.core.transfer.processors.submit_unsubmitted_transfers import (
    SubmitUnsubmittedTransfers,
    SubmitUnsubmittedTransfersRequest,
)
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepositoryInterface,
)
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepositoryInterface,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.core.transfer.processors.weekly_create_transfer import (
    WeeklyCreateTransferRequest,
    WeeklyCreateTransfer,
)
from app.payout.repository.maindb.transfer import TransferRepositoryInterface


class TransferProcessors:
    logger: BoundLogger
    stripe: StripeAsyncClient
    transfer_repo: TransferRepositoryInterface
    payment_account_repo: PaymentAccountRepositoryInterface
    stripe_transfer_repo: StripeTransferRepositoryInterface
    managed_account_transfer_repo: ManagedAccountTransferRepositoryInterface
    transaction_repo: TransactionRepositoryInterface
    payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface
    payment_lock_manager: Aioredlock

    def __init__(
        self,
        logger: BoundLogger,
        stripe: StripeAsyncClient,
        transfer_repo: TransferRepositoryInterface,
        payment_account_repo: PaymentAccountRepositoryInterface,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
        managed_account_transfer_repo: ManagedAccountTransferRepositoryInterface,
        transaction_repo: TransactionRepositoryInterface,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface,
        payment_lock_manager: Aioredlock,
    ):
        self.logger = logger
        self.stripe = stripe
        self.transfer_repo = transfer_repo
        self.payment_account_repo = payment_account_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.managed_account_transfer_repo = managed_account_transfer_repo
        self.transaction_repo = transaction_repo
        self.payment_account_edit_history_repo = payment_account_edit_history_repo
        self.payment_lock_manager = payment_lock_manager

    async def create_transfer(self, request: CreateTransferRequest):
        create_transfer_op = CreateTransfer(
            logger=self.logger,
            request=request,
            transfer_repo=self.transfer_repo,
            payment_account_repo=self.payment_account_repo,
            payment_account_edit_history_repo=self.payment_account_edit_history_repo,
            transaction_repo=self.transaction_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
            payment_lock_manager=self.payment_lock_manager,
        )
        return await create_transfer_op.execute()

    async def submit_transfer(self, request: SubmitTransferRequest):
        submit_transfer_op = SubmitTransfer(
            logger=self.logger,
            request=request,
            stripe=self.stripe,
            transfer_repo=self.transfer_repo,
            payment_account_repo=self.payment_account_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
            managed_account_transfer_repo=self.managed_account_transfer_repo,
            transaction_repo=self.transaction_repo,
            payment_account_edit_history_repo=self.payment_account_edit_history_repo,
        )
        return await submit_transfer_op.execute()

    async def weekly_create_transfer(self, request: WeeklyCreateTransferRequest):
        weekly_create_transfer_op = WeeklyCreateTransfer(
            logger=self.logger,
            request=request,
            transfer_repo=self.transfer_repo,
            payment_lock_manager=self.payment_lock_manager,
            payment_account_edit_history_repo=self.payment_account_edit_history_repo,
            payment_account_repo=self.payment_account_repo,
            transaction_repo=self.transaction_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
        )
        return await weekly_create_transfer_op.execute()

    async def submit_unsubmitted_transfers(
        self, request: SubmitUnsubmittedTransfersRequest
    ):
        submit_unsubmitted_transfers_op = SubmitUnsubmittedTransfers(
            request=request,
            transfer_repo=self.transfer_repo,
            transaction_repo=self.transaction_repo,
            managed_account_transfer_repo=self.managed_account_transfer_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
            payment_account_repo=self.payment_account_repo,
            payment_account_edit_history_repo=self.payment_account_edit_history_repo,
            stripe=self.stripe,
        )
        return await submit_unsubmitted_transfers_op.execute()
