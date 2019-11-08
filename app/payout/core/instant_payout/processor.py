from aioredlock import Aioredlock
from structlog import BoundLogger

from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.core.errors import (
    InstantPayoutBadRequestError,
    InstantPayoutErrorCode,
    instant_payout_error_message_maps,
)
from app.payout.core.instant_payout.models import (
    EligibilityCheckRequest,
    InternalPaymentEligibility,
    CreateAndSubmitInstantPayoutRequest,
    CreateAndSubmitInstantPayoutResponse,
    GetPayoutCardRequest,
    InstantPayoutFees,
    VerifyTransactionsRequest,
    CreatePayoutsRequest,
    CheckSMABalanceRequest,
    SMATransferRequest,
    SubmitInstantPayoutRequest,
)
from app.payout.core.instant_payout.processors.check_eligibility import (
    CheckPayoutAccount,
    CheckPayoutCard,
    CheckPayoutAccountBalance,
    CheckInstantPayoutDailyLimit,
)
from app.payout.core.instant_payout.processors.get_payout_card import GetPayoutCard
from app.payout.core.instant_payout.processors.pgp.check_sma_balance import (
    CheckSMABalance,
)
from app.payout.core.instant_payout.processors.pgp.submit_instant_payout import (
    SubmitInstantPayout,
)
from app.payout.core.instant_payout.processors.pgp.submit_sma_transfer import (
    SubmitSMATransfer,
)
from app.payout.core.instant_payout.processors.verify_transactions import (
    VerifyTransactions,
)
from app.payout.core.instant_payout.utils import create_idempotency_key
from app.payout.repository.bankdb.payout import PayoutRepositoryInterface
from app.payout.repository.bankdb.payout_card import PayoutCardRepositoryInterface
from app.payout.repository.bankdb.payout_method import PayoutMethodRepositoryInterface
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepository,
)
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
    stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository
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
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
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
        self.stripe_managed_account_transfer_repo = stripe_managed_account_transfer_repo
        self.stripe_payout_request_repo = stripe_payout_request_repo
        self.transaction_repo = transaction_repo
        self.stripe = stripe
        self.payment_lock_manager = payment_lock_manager

    async def create_and_submit_instant_payout(
        self, request: CreateAndSubmitInstantPayoutRequest
    ) -> CreateAndSubmitInstantPayoutResponse:

        # Check Payout Account status, it's required to perform an instant payout
        check_request = EligibilityCheckRequest(
            payout_account_id=request.payout_account_id
        )
        check_payout_account_op = CheckPayoutAccount(
            check_request, self.payout_account_repo, self.logger
        )
        result = await check_payout_account_op.execute()
        if result.eligible is False:
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.INVALID_REQUEST,
                error_message=str(result.reason),
            )

        # Get Payout Card. If stripe card id provided, check its existence; else retrieve default payout card
        get_payout_card_request = GetPayoutCardRequest(
            payout_account_id=request.payout_account_id, stripe_card_id=request.card
        )
        get_payout_card_op = GetPayoutCard(
            request=get_payout_card_request,
            payout_card_repo=self.payout_card_repo,
            payout_method_repo=self.payout_method_repo,
            logger=self.logger,
        )
        payout_card_response = await get_payout_card_op.execute()
        payout_method_id = payout_card_response.payout_card_id
        payout_card_stripe_id = payout_card_response.stripe_card_id

        # raise error if amount is less than fee
        if request.amount < InstantPayoutFees.STANDARD_FEE:
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.AMOUNT_LESS_THAN_FEE,
                error_message=instant_payout_error_message_maps[
                    InstantPayoutErrorCode.AMOUNT_LESS_THAN_FEE
                ],
            )

        # verify transactions and get all unpaid transaction ids
        verify_transactions_request = VerifyTransactionsRequest(
            payout_account_id=request.payout_account_id, amount=request.amount
        )
        verify_transactions_request_op = VerifyTransactions(
            request=verify_transactions_request,
            transaction_repo=self.transaction_repo,
            logger=self.logger,
        )

        verify_transactions_response = await verify_transactions_request_op.execute()
        transaction_ids = verify_transactions_response.transaction_ids
        idempotency_key = create_idempotency_key(prefix=None)

        # Atomically create payout, fee transaction & attach payout_id to transactions
        create_payout_request = CreatePayoutsRequest(
            payout_account_id=request.payout_account_id,
            amount=request.amount,
            currency=request.currency,
            idempotency_key=idempotency_key,
            payout_method_id=payout_method_id,
            transaction_ids=transaction_ids,
            fee=InstantPayoutFees.STANDARD_FEE,
        )
        create_payout_response = await self.payout_repo.create_payout_and_attach_to_transactions(
            request=create_payout_request
        )

        # Get stripe_id of StripeManagedAccount
        payout_account = await self.payout_account_repo.get_payment_account_by_id(
            payment_account_id=request.payout_account_id
        )

        if not payout_account:
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.PAYOUT_ACCOUNT_NOT_EXIST,
                error_message=instant_payout_error_message_maps[
                    InstantPayoutErrorCode.PAYOUT_ACCOUNT_NOT_EXIST
                ],
            )

        if not payout_account.account_id:
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.PGP_ACCOUNT_NOT_SETUP,
                error_message=instant_payout_error_message_maps[
                    InstantPayoutErrorCode.PGP_ACCOUNT_NOT_SETUP
                ],
            )

        stripe_managed_account = await self.payout_account_repo.get_stripe_managed_account_by_id(
            payout_account.account_id
        )
        if not stripe_managed_account:
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.PGP_ACCOUNT_NOT_SETUP,
                error_message=instant_payout_error_message_maps[
                    InstantPayoutErrorCode.PGP_ACCOUNT_NOT_SETUP
                ],
            )

        # Check Stripe Connected Account Balance
        check_sma_balance_request = CheckSMABalanceRequest(
            stripe_managed_account_id=stripe_managed_account.stripe_id,
            country=stripe_managed_account.country_shortname,
        )
        check_sma_balance_op = CheckSMABalance(
            request=check_sma_balance_request,
            stripe_client=self.stripe,
            logger=self.logger,
        )
        sma_balance = await check_sma_balance_op.execute()
        if sma_balance.balance < create_payout_response.amount:
            # Submit SMA Transfer
            amount_needed = create_payout_response.amount - sma_balance.balance
            sma_transfer_request = SMATransferRequest(
                payout_id=create_payout_response.payout_id,
                transaction_ids=transaction_ids,
                amount=amount_needed,
                currency=request.currency,
                destination=stripe_managed_account.stripe_id,
                country=stripe_managed_account.country_shortname.upper(),
                idempotency_key=create_idempotency_key(prefix=None),
            )
            submit_sma_transfer_op = SubmitSMATransfer(
                request=sma_transfer_request,
                stripe_managed_account_transfer_repo=self.stripe_managed_account_transfer_repo,
                stripe_client=self.stripe,
                payout_repo=self.payout_repo,
                transaction_repo=self.transaction_repo,
                logger=self.logger,
            )
            await submit_sma_transfer_op.execute()

        # Submit Instant Payout
        submit_instant_payout_request = SubmitInstantPayoutRequest(
            payout_id=create_payout_response.payout_id,
            transaction_ids=transaction_ids,
            country=stripe_managed_account.country_shortname.upper(),
            stripe_account_id=stripe_managed_account.stripe_id,
            amount=create_payout_response.amount,
            currency=request.currency,
            payout_method_id=payout_method_id,
            destination=payout_card_stripe_id,
            idempotency_key=idempotency_key,
        )

        submit_instant_payout_op = SubmitInstantPayout(
            request=submit_instant_payout_request,
            stripe_client=self.stripe,
            stripe_payout_request_repo=self.stripe_payout_request_repo,
            payout_repo=self.payout_repo,
            transaction_repo=self.transaction_repo,
            logger=self.logger,
        )
        submit_instant_payout_response = await submit_instant_payout_op.execute()

        return CreateAndSubmitInstantPayoutResponse(
            payout_id=create_payout_response.payout_id,
            amount=submit_instant_payout_response.amount,
            currency=submit_instant_payout_response.currency,
            fee=create_payout_response.fee,
            status=submit_instant_payout_response.status,
            card=submit_instant_payout_response.destination,
            created_at=create_payout_response.created_at,
        )

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
