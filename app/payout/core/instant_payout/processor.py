from aioredlock import Aioredlock
from structlog import BoundLogger

from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.core.instant_payout.models import (
    EligibilityCheckRequest,
    InternalPaymentEligibility,
)
from app.payout.core.instant_payout.processors.check_eligibility import (
    CheckPayoutAccount,
    CheckPayoutCard,
    CheckPayoutAccountBalance,
    CheckInstantPayoutDailyLimit,
)
from app.payout.repository.bankdb.payout import PayoutRepositoryInterface
from app.payout.repository.bankdb.payout_card import PayoutCardRepositoryInterface
from app.payout.repository.bankdb.payout_method import PayoutMethodRepositoryInterface
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepositoryInterface,
)
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)


class InstantPayoutProcessors:
    logger: BoundLogger
    payout_account_repo: PaymentAccountRepositoryInterface
    payout_card_repo: PayoutCardRepositoryInterface
    payout_method_repo: PayoutMethodRepositoryInterface
    payout_repo: PayoutRepositoryInterface
    stripe_payout_request_repo: StripePayoutRequestRepositoryInterface
    stripe: StripeAsyncClient
    payment_lock_manager: Aioredlock

    def __init__(
        self,
        logger: BoundLogger,
        payout_account_repo: PaymentAccountRepositoryInterface,
        payout_card_repo: PayoutCardRepositoryInterface,
        payout_method_repo: PayoutMethodRepositoryInterface,
        payout_repo: PayoutRepositoryInterface,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        transaction_repo: TransactionRepositoryInterface,
        stripe: StripeAsyncClient,
        payment_lock_manager: Aioredlock,
    ):
        self.logger = logger
        self.payout_account_repo = payout_account_repo
        self.payout_card_repo = payout_card_repo
        self.payout_method_repo = payout_method_repo
        self.payout_repo = payout_repo
        self.stripe_payout_request_repo = stripe_payout_request_repo
        self.transaction_repo = transaction_repo
        self.stripe = stripe
        self.payment_lock_manager = payment_lock_manager

    async def create_and_submit_instant_payout(self):
        pass

    async def check_instant_payout_eligibility(
        self, request: EligibilityCheckRequest
    ) -> InternalPaymentEligibility:
        check_payout_account_op = CheckPayoutAccount(
            request, self.payout_account_repo, self.logger
        )
        payout_account_eligibility = await check_payout_account_op.execute()
        # If payout account record does not exist, fee will be None. Otherwise, fee wil be populated into response.
        fee = payout_account_eligibility.fee
        # Check payout account status
        if payout_account_eligibility.eligible is False:
            return InternalPaymentEligibility(
                eligible=False, reason=payout_account_eligibility.reason, fee=fee
            )

        currency = payout_account_eligibility.currency

        # Check Payout Card status
        check_payout_card_op = CheckPayoutCard(
            request, self.payout_method_repo, self.payout_card_repo, self.logger
        )
        payout_card_eligibility = await check_payout_card_op.execute()
        if payout_card_eligibility.eligible is False:
            return InternalPaymentEligibility(
                eligible=False,
                reason=payout_card_eligibility.reason,
                details=payout_card_eligibility.details,
                fee=fee,
            )

        # Check Balance status
        check_balance_op = CheckPayoutAccountBalance(
            request, self.transaction_repo, self.logger
        )
        balance_eligibility = await check_balance_op.execute()
        balance = balance_eligibility.balance

        if balance_eligibility.eligible is False:
            return InternalPaymentEligibility(
                eligible=False,
                reason=balance_eligibility.reason,
                balance=balance,
                currency=currency,
                fee=fee,
            )

        # Check Daily Limit Status
        daily_limit_op = CheckInstantPayoutDailyLimit(
            request, self.payout_repo, self.logger
        )
        daily_limit_eligibility = await daily_limit_op.execute()
        if daily_limit_eligibility.eligible is False:
            return InternalPaymentEligibility(
                eligible=False,
                reason=daily_limit_eligibility.reason,
                balance=balance,
                currency=currency,
                fee=fee,
            )

        return InternalPaymentEligibility(
            eligible=True, balance=balance, currency=currency, fee=fee
        )
