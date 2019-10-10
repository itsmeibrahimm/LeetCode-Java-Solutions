from structlog.stdlib import BoundLogger
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.core.transfer.processors.submit_transfer import (
    SubmitTransferRequest,
    SubmitTransfer,
)
from app.payout.repository.maindb.transfer import TransferRepositoryInterface


class TransferProcessors:
    logger: BoundLogger
    stripe: StripeAsyncClient
    transfer_repo: TransferRepositoryInterface

    def __init__(
        self,
        logger: BoundLogger,
        stripe: StripeAsyncClient,
        transfer_repo: TransferRepositoryInterface,
    ):
        self.logger = logger
        self.stripe = stripe
        self.transfer_repo = transfer_repo

    async def submit_transfer(self, request: SubmitTransferRequest):
        submit_transfer_op = SubmitTransfer(
            logger=self.logger,
            request=request,
            stripe=self.stripe,
            transfer_repo=self.transfer_repo,
        )
        return await submit_transfer_op.execute()
