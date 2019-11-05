from datetime import datetime, timedelta

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from structlog.stdlib import BoundLogger
from typing import Union, Optional
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.core.transfer.processors.submit_transfer import (
    SubmitTransferRequest,
    SubmitTransfer,
)
from app.payout.models import PayoutTargetType, TransferMethodType
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
from app.payout.repository.maindb.transfer import TransferRepositoryInterface


class SubmitUnsubmittedTransfersResponse(OperationResponse):
    pass


class SubmitUnsubmittedTransfersRequest(OperationRequest):
    statement_descriptor: str
    target_id: Optional[str] = None
    target_type: Optional[PayoutTargetType] = None
    method: Optional[str] = TransferMethodType.STRIPE
    submitted_by: Optional[int] = None


class SubmitUnsubmittedTransfers(
    AsyncOperation[
        SubmitUnsubmittedTransfersRequest, SubmitUnsubmittedTransfersResponse
    ]
):
    """
    Processor to submit unsubmitted transfers, triggered by cron_submit_unsubmitted_transfers
    """

    transfer_repo: TransferRepositoryInterface
    payment_account_repo: PaymentAccountRepositoryInterface
    stripe_transfer_repo: StripeTransferRepositoryInterface
    managed_account_transfer_repo: ManagedAccountTransferRepositoryInterface
    transaction_repo: TransactionRepositoryInterface
    payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface

    def __init__(
        self,
        request: SubmitUnsubmittedTransfersRequest,
        *,
        transfer_repo: TransferRepositoryInterface,
        payment_account_repo: PaymentAccountRepositoryInterface,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
        managed_account_transfer_repo: ManagedAccountTransferRepositoryInterface,
        transaction_repo: TransactionRepositoryInterface,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface,
        stripe: StripeAsyncClient,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transfer_repo = transfer_repo
        self.payment_account_repo = payment_account_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.managed_account_transfer_repo = managed_account_transfer_repo
        self.transaction_repo = transaction_repo
        self.payment_account_edit_history_repo = payment_account_edit_history_repo
        self.stripe = stripe

    async def _execute(self) -> SubmitUnsubmittedTransfersResponse:
        created_before = datetime.utcnow() - timedelta(hours=3)
        transfer_ids = await self.transfer_repo.get_unsubmitted_transfer_ids(
            created_before=created_before
        )
        # todo: investigate how to use doorstats.gauge here

        self.logger.info(
            "[weekly_submit_transfers]: submitting unsubmitted transfers",
            unsubmitted_transfer_count=len(transfer_ids),
        )
        for transfer_id in transfer_ids:
            # todo: put submit_transfer into queue
            submit_transfer_request = SubmitTransferRequest(
                transfer_id=transfer_id,
                statement_descriptor=self.request.statement_descriptor,
                target_id=self.request.target_id,
                target_type=self.request.target_type,
                method=self.request.method,
                retry=True,
                submitted_by=self.request.submitted_by,
            )
            submit_transfer_op = SubmitTransfer(
                logger=self.logger,
                request=submit_transfer_request,
                transfer_repo=self.transfer_repo,
                payment_account_edit_history_repo=self.payment_account_edit_history_repo,
                payment_account_repo=self.payment_account_repo,
                stripe_transfer_repo=self.stripe_transfer_repo,
                managed_account_transfer_repo=self.managed_account_transfer_repo,
                transaction_repo=self.transaction_repo,
                stripe=self.stripe,
            )
            await submit_transfer_op.execute()

        return SubmitUnsubmittedTransfersResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, SubmitUnsubmittedTransfersResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION
