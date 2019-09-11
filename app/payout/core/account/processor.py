from app.commons.context.logger import Log
from app.payout.core.account.processors.create_account import (
    CreatePayoutAccountRequest,
    CreatePayoutAccount,
)
from app.payout.core.account.processors.create_standard_payout import (
    CreateStandardPayoutRequest,
    CreateStandardPayoutResponse,
    CreateStandardPayout,
)
from app.payout.core.account.processors.create_instant_payout import (
    CreateInstantPayoutRequest,
    CreateInstantPayoutResponse,
    CreateInstantPayout,
)
from app.payout.core.account.processors.get_account import (
    GetPayoutAccountRequest,
    PayoutAccountInternal,
    GetPayoutAccount,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepositoryInterface,
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
    stripe_payout_request_repo: StripePayoutRequestRepositoryInterface

    def __init__(
        self,
        logger: Log,
        payment_account_repo: PaymentAccountRepositoryInterface,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
    ):
        self.logger = logger
        self.payment_account_repo = payment_account_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.stripe_payout_request_repo = stripe_payout_request_repo

    async def create_payout_account(
        self, request: CreatePayoutAccountRequest
    ) -> PayoutAccountInternal:
        create_account_op = CreatePayoutAccount(
            logger=self.logger,
            payment_account_repo=self.payment_account_repo,
            request=request,
        )
        return await create_account_op.execute()

    async def get_payout_account(
        self, request: GetPayoutAccountRequest
    ) -> PayoutAccountInternal:
        get_account_op = GetPayoutAccount(
            logger=self.logger,
            payment_account_repo=self.payment_account_repo,
            request=request,
        )
        return await get_account_op.execute()

    async def create_standard_payout(
        self, request: CreateStandardPayoutRequest
    ) -> CreateStandardPayoutResponse:
        # TODO: A repo for maindb.managed_account_transfer is needed
        create_standard_payout_op = CreateStandardPayout(
            logger=self.logger,
            stripe_transfer_repo=self.stripe_transfer_repo,
            request=request,
        )
        return await create_standard_payout_op.execute()

    async def create_instant_payout(
        self, request: CreateInstantPayoutRequest
    ) -> CreateInstantPayoutResponse:
        # TODO: A repo for bankdb.transfers is needed
        create_instant_payout_op = CreateInstantPayout(
            logger=self.logger,
            stripe_payout_request_repo=self.stripe_payout_request_repo,
            request=request,
        )
        return await create_instant_payout_op.execute()
