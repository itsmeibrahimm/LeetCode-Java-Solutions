from app.commons.context.logger import Log
from app.payout.core.account.processors.create_account import (
    CreatePayoutAccountRequest,
    CreatePayoutAccountResponse,
    CreatePayoutAccount,
)
from app.payout.core.account.processors.create_standard_payout import (
    CreateStandardPayoutRequest,
    CreateStandardPayoutResponse,
    CreateStandardPayout,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)


class PayoutAccountProcessors:
    logger: Log
    payment_account_repo: PaymentAccountRepositoryInterface
    stripe_transfer_repo: StripeTransferRepositoryInterface

    def __init__(
        self,
        logger: Log,
        payment_account_repo: PaymentAccountRepositoryInterface,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
    ):
        self.logger = logger
        self.payment_account_repo = payment_account_repo
        self.stripe_transfer_repo = stripe_transfer_repo

    async def create_payout_account(
        self, request: CreatePayoutAccountRequest
    ) -> CreatePayoutAccountResponse:
        create_account_op = CreatePayoutAccount(
            logger=self.logger,
            payment_account_repo=self.payment_account_repo,
            request=request,
        )
        return await create_account_op.execute()

    async def create_standard_payout(
        self, request: CreateStandardPayoutRequest
    ) -> CreateStandardPayoutResponse:
        create_standard_payout_op = CreateStandardPayout(
            logger=self.logger,
            stripe_transfer_repo=self.stripe_transfer_repo,
            request=request,
        )
        return await create_standard_payout_op.execute()
