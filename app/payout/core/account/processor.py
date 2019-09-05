from app.commons.context.logger import Log
from app.payout.core.account.processors.create_account import (
    CreatePayoutAccountRequest,
    CreatePayoutAccountResponse,
    CreatePayoutAccount,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)


class PayoutAccountProcessors:
    logger: Log
    payment_account_repo: PaymentAccountRepositoryInterface

    def __init__(
        self, logger: Log, payment_account_repo: PaymentAccountRepositoryInterface
    ):
        self.logger = logger
        self.payment_account_repo = payment_account_repo

    async def create_payout_account(
        self, request: CreatePayoutAccountRequest
    ) -> CreatePayoutAccountResponse:
        processor = CreatePayoutAccount(
            logger=self.logger,
            payment_account_repo=self.payment_account_repo,
            request=request,
        )
        return await processor.process()
