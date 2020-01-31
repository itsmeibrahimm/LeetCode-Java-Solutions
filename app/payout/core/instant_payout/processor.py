import hashlib

from aioredlock import Aioredlock
from structlog import BoundLogger

from app.commons.lock.lockable import Lockable
from app.commons.lock.locks import PaymentLock
from app.commons.lock.payment_db_lock import PaymentDBLock
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.constants import PAYOUT_ACCOUNT_LOCK_DEFAULT_TIMEOUT
from app.payout.core.account.utils import COUNTRY_TO_CURRENCY_CODE
from app.payout.core.errors import (
    InstantPayoutBadRequestError,
    InstantPayoutErrorCode,
    instant_payout_error_message_maps,
)
from app.payout.core.feature_flags import enable_payment_db_lock_for_payout
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
    GetPayoutStreamRequest,
    GetPayoutStreamResponse,
)
from app.payout.core.instant_payout.processors.check_eligibility import (
    CheckPayoutAccount,
    CheckPayoutCard,
    CheckPayoutAccountBalance,
    CheckInstantPayoutDailyLimit,
)
from app.payout.core.instant_payout.processors.get_payout_card import GetPayoutCard
from app.payout.core.instant_payout.processors.get_payout_stream import GetPayoutStream
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
from app.payout.core.instant_payout.utils import (
    create_idempotency_key,
    get_payout_account_lock_name,
)
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
    payout_lock_repo: Lockable

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
        payout_lock_repo: Lockable,
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
        self.payout_lock_repo = payout_lock_repo

    async def create_and_submit_instant_payout(
        self, request: CreateAndSubmitInstantPayoutRequest
    ) -> CreateAndSubmitInstantPayoutResponse:

        self.logger.info(
            "[Instant Payout Submit]: Creating and submitting instant payout",
            request=request.dict(),
        )

        # 1. Check Payout Account status, it's required to perform an instant payout
        check_request = EligibilityCheckRequest(
            payout_account_id=request.payout_account_id
        )
        check_payout_account_op = CheckPayoutAccount(
            check_request, self.payout_account_repo, self.logger
        )
        result = await check_payout_account_op.execute()
        if result.eligible is False:
            self.logger.warn(
                "[Instant Payout Submit]: fail due to payout account ineligible",
                request=request.dict(),
                eligibility=result.dict(),
            )
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.INVALID_REQUEST,
                error_message=str(result.reason),
            )

        # 2. Get Payout Card. If stripe card id provided, check its existence; else retrieve default payout card
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

        # 3. Check input amount, raise error if amount is less than fee
        if request.amount < InstantPayoutFees.STANDARD_FEE:
            self.logger.warn(
                "[Instant Payout Submit]: fail due to amount less than fee",
                request=request.dict(),
            )
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.AMOUNT_LESS_THAN_FEE,
                error_message=instant_payout_error_message_maps[
                    InstantPayoutErrorCode.AMOUNT_LESS_THAN_FEE
                ],
            )

        # 4. Get stripe_id of StripeManagedAccount, it's required to submit sma transfer
        payout_account = await self.payout_account_repo.get_payment_account_by_id(
            payment_account_id=request.payout_account_id
        )

        if not payout_account:
            self.logger.warn(
                "[Instant Payout Submit]: fail due to payout account not exist",
                request=request.dict(),
            )
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.PAYOUT_ACCOUNT_NOT_EXIST,
                error_message=instant_payout_error_message_maps[
                    InstantPayoutErrorCode.PAYOUT_ACCOUNT_NOT_EXIST
                ],
            )

        if not payout_account.account_id:
            self.logger.warn(
                "[Instant Payout Submit]: fail due to pgp account id not exist",
                request=request.dict(),
            )
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
            self.logger.warn(
                "[Instant Payout Submit]: fail due to pgp account not exist",
                request=request.dict(),
            )
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.PGP_ACCOUNT_NOT_SETUP,
                error_message=instant_payout_error_message_maps[
                    InstantPayoutErrorCode.PGP_ACCOUNT_NOT_SETUP
                ],
            )

        if (
            COUNTRY_TO_CURRENCY_CODE.get(
                stripe_managed_account.country_shortname.upper(), None
            )
            != request.currency.upper()
        ):
            self.logger.warn(
                "[Instant Payout Submit]: fail due to currency mismatch",
                request=request.dict(),
            )
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.CURRENCY_MISMATCH,
                error_message=instant_payout_error_message_maps[
                    InstantPayoutErrorCode.CURRENCY_MISMATCH
                ],
            )

        # 5. verify transactions and get all unpaid transaction ids
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

        self.logger.info(
            "[Instant Payout Submit]: Get all transactions",
            request=request.dict(),
            transaction_ids=transaction_ids,
        )

        # 6. Atomically create payout, fee transaction & attach payout_id to transactions
        create_payout_request = CreatePayoutsRequest(
            payout_account_id=request.payout_account_id,
            amount=request.amount,
            currency=request.currency,
            idempotency_key=idempotency_key,
            payout_method_id=payout_method_id,
            transaction_ids=transaction_ids,
            fee=InstantPayoutFees.STANDARD_FEE,
        )
        if enable_payment_db_lock_for_payout(request.payout_account_id):
            self.logger.info(
                "[Instant Payout Submit]: Entering PaymentDBLock to create instant payout",
                payout_account_id=request.payout_account_id,
            )
            hashed_payout_account = hashlib.sha256(
                str(request.payout_account_id).encode("utf-8")
            ).hexdigest()
            async with PaymentDBLock(self.payout_lock_repo, hashed_payout_account):
                self.logger.info(
                    "[Instant Payout Submit]: Creating instant payout in PaymentDBLock",
                    payout_account_id=request.payout_account_id,
                )
                create_payout_response = await self.payout_repo.create_payout_and_attach_to_transactions(
                    request=create_payout_request
                )
                self.logger.info(
                    "[Instant Payout Submit]: Created instant payout in PaymentDBLock",
                    payout_account_id=request.payout_account_id,
                )
        else:
            lock_name = get_payout_account_lock_name(request.payout_account_id)
            async with PaymentLock(
                lock_name,
                self.payment_lock_manager,
                lock_timeout=PAYOUT_ACCOUNT_LOCK_DEFAULT_TIMEOUT,
            ):
                create_payout_response = await self.payout_repo.create_payout_and_attach_to_transactions(
                    request=create_payout_request
                )
        self.logger.info(
            "[Instant Payout Submit]: Created Instant Payout",
            create_payout_request=create_payout_request.dict(),
            create_payout_response=create_payout_response.dict(),
        )

        # 7. Check Stripe Connected Account Balance
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

        # 8. Submit SMA Transfer if needed
        if sma_balance.balance < create_payout_response.amount:
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

        # 9. Submit Instant Payout
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

        self.logger.info(
            "[Instant Payout Submit]: Succeed to submit Instant Payout",
            request=request.dict(),
            response=submit_instant_payout_response.dict(),
        )

        return CreateAndSubmitInstantPayoutResponse(
            payout_account_id=request.payout_account_id,
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
        """Check Instant Payout Payment Eligibility Status.

        Eligibility Checks include:
            - PayoutAccount Eligibility
            - PayoutCard Eligibility
            - Balance Eligibility
            - Daily Limit Eligibility

        :param request: Eligibility check request
        :type request: EligibilityCheckRequest
        :return: eligibility: eligibility status
        :rtype: eligibility: InternalPaymentEligibility
        """
        self.logger.info("[Checking Payment Eligibility]", request=request.dict())
        check_payout_account_op = CheckPayoutAccount(
            request, self.payout_account_repo, self.logger
        )
        payout_account_eligibility = await check_payout_account_op.execute()
        # If payout account record does not exist, fee will be None. Otherwise, fee wil be populated into response.
        fee = payout_account_eligibility.fee
        self.logger.info(
            "[Payout Account Eligibility]",
            eligibility=payout_account_eligibility.dict(),
        )
        # Check payout account status
        if payout_account_eligibility.eligible is False:
            return InternalPaymentEligibility(
                payout_account_id=request.payout_account_id,
                eligible=False,
                reason=payout_account_eligibility.reason,
                details=payout_account_eligibility.details,
                fee=fee,
            )

        currency = payout_account_eligibility.currency

        # Check Payout Card status
        check_payout_card_op = CheckPayoutCard(
            request, self.payout_method_repo, self.payout_card_repo, self.logger
        )
        payout_card_eligibility = await check_payout_card_op.execute()
        self.logger.info(
            "[Payout Card Eligibility]", eligibility=payout_card_eligibility.dict()
        )
        if payout_card_eligibility.eligible is False:
            return InternalPaymentEligibility(
                payout_account_id=request.payout_account_id,
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
        self.logger.info(
            "[Balance Eligibility]", eligibility=balance_eligibility.dict()
        )
        if balance_eligibility.eligible is False:
            return InternalPaymentEligibility(
                payout_account_id=request.payout_account_id,
                eligible=False,
                reason=balance_eligibility.reason,
                details=balance_eligibility.details,
                balance=balance,
                currency=currency,
                fee=fee,
            )

        # Check Daily Limit Status
        daily_limit_op = CheckInstantPayoutDailyLimit(
            request, self.payout_repo, self.logger
        )
        daily_limit_eligibility = await daily_limit_op.execute()
        self.logger.info(
            "[Daily Limit Eligibility]", eligibility=daily_limit_eligibility.dict()
        )
        if daily_limit_eligibility.eligible is False:
            return InternalPaymentEligibility(
                payout_account_id=request.payout_account_id,
                eligible=False,
                reason=daily_limit_eligibility.reason,
                details=daily_limit_eligibility.details,
                balance=balance,
                currency=currency,
                fee=fee,
            )

        return InternalPaymentEligibility(
            payout_account_id=request.payout_account_id,
            eligible=True,
            balance=balance,
            currency=currency,
            fee=fee,
        )

    async def get_instant_payout_stream_by_payout_account_id(
        self, request: GetPayoutStreamRequest
    ) -> GetPayoutStreamResponse:
        get_payout_stream_op = GetPayoutStream(
            request=request,
            payout_repo=self.payout_repo,
            stripe_payout_request_repo=self.stripe_payout_request_repo,
            logger=self.logger,
        )
        return await get_payout_stream_op.execute()
