from typing import Union

import pytz
from structlog import BoundLogger
from datetime import datetime
from app.commons.core.errors import PaymentError
from app.commons.core.processor import AsyncOperation
from app.payout.core.account.utils import COUNTRY_TO_CURRENCY_CODE
from app.payout.core.instant_payout.models import (
    PaymentEligibilityReasons,
    InstantPayoutSupportedCountries,
    PayoutAccountEligibility,
    InstantPayoutSupportedEntities,
    BalanceEligibility,
    InstantPayoutFees,
    PayoutCardEligibility,
    InstantPayoutCardChangeBlockTimeInDays,
    InstantPayoutDailyLimitEligibility,
    InstantPayoutDailyLimitCheckStatuses,
    EligibilityCheckRequest,
    InstantPayoutSupportedPGPAccountTypes,
)
from app.payout.repository.bankdb.payout import PayoutRepositoryInterface
from app.payout.repository.bankdb.payout_card import PayoutCardRepositoryInterface
from app.payout.repository.bankdb.payout_method import PayoutMethodRepositoryInterface
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)


class CheckPayoutAccount(
    AsyncOperation[EligibilityCheckRequest, PayoutAccountEligibility]
):
    """Instant Payout Payout Account Eligibility Check.

    Check payout account status, including,
        - payout account existence
        - payout account entity eligible status
        - payout pgp account existence
        - payout pgp account country eligible status
        - payout pgp account verification status
    """

    def __init__(
        self,
        request: EligibilityCheckRequest,
        payout_account_repo: PaymentAccountRepositoryInterface,
        logger: BoundLogger = None,
    ):

        super().__init__(request, logger)
        self.payout_account_id = request.payout_account_id
        self.payout_account_repo = payout_account_repo

    async def _execute(self) -> PayoutAccountEligibility:
        # Check Payout Account existence in db
        payout_account = await self.payout_account_repo.get_payment_account_by_id(
            payment_account_id=self.payout_account_id
        )
        if payout_account is None:
            return PayoutAccountEligibility(
                eligible=False,
                reason=PaymentEligibilityReasons.PAYOUT_ACCOUNT_NOT_EXIST,
            )
        if payout_account.entity not in InstantPayoutSupportedEntities:
            return PayoutAccountEligibility(
                eligible=False,
                reason=PaymentEligibilityReasons.PAYOUT_ACCOUNT_TYPE_NOT_SUPPORTED,
                fee=InstantPayoutFees.STANDARD_FEE,
            )
        # Check PGP account id existence
        if (not payout_account.account_id) or (
            payout_account.account_type not in InstantPayoutSupportedPGPAccountTypes
        ):
            return PayoutAccountEligibility(
                eligible=False,
                reason=PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_SETUP,
                fee=InstantPayoutFees.STANDARD_FEE,
            )

        # Check PGP record existence in db
        pgp_account = await self.payout_account_repo.get_stripe_managed_account_by_id(
            payout_account.account_id
        )
        if pgp_account is None:
            return PayoutAccountEligibility(
                eligible=False,
                reason=PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_EXIST,
                fee=InstantPayoutFees.STANDARD_FEE,
            )

        # Check PGP country is supported or not
        if (
            not pgp_account.country_shortname
            or pgp_account.country_shortname.upper()
            not in InstantPayoutSupportedCountries
        ):
            return PayoutAccountEligibility(
                eligible=False,
                reason=PaymentEligibilityReasons.PAYOUT_ACCOUNT_COUNTRY_NOT_SUPPORTED,
                fee=InstantPayoutFees.STANDARD_FEE,
            )

        currency = COUNTRY_TO_CURRENCY_CODE[pgp_account.country_shortname].lower()

        # Check PGP account is verified or not
        if pgp_account.verification_disabled_reason:
            return PayoutAccountEligibility(
                eligible=False,
                reason=PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_VERIFIED,
                fee=InstantPayoutFees.STANDARD_FEE,
            )

        return PayoutAccountEligibility(
            eligible=True, currency=currency, fee=InstantPayoutFees.STANDARD_FEE
        )

    def _handle_exception(
        self, internal_exec: Exception
    ) -> Union[PaymentError, PayoutAccountEligibility]:
        raise


class CheckPayoutCard(AsyncOperation[EligibilityCheckRequest, PayoutCardEligibility]):
    """Instant Payout Payout Card Change Status Check.

    Check payout card status, including
        - Payout card setup status,
        - Recently changed payout card status (fraud control)
    """

    def __init__(
        self,
        request: EligibilityCheckRequest,
        payout_method_repo: PayoutMethodRepositoryInterface,
        payout_card_repo: PayoutCardRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.payout_account_id = request.payout_account_id
        self.payout_method_repo = payout_method_repo
        self.payout_card_repo = payout_card_repo

    async def _execute(self) -> PayoutCardEligibility:
        # get all payout methods
        payout_methods = await self.payout_method_repo.list_payout_methods_by_payout_account_id(
            payout_account_id=self.payout_account_id
        )

        payout_method_ids = [payout_method.id for payout_method in payout_methods]
        # Pass in payout method ids since payout_method and payout_card is linked by same id
        payout_cards = await self.payout_card_repo.list_payout_cards_by_ids(
            payout_method_ids
        )

        if not payout_cards:
            return PayoutCardEligibility(
                eligible=False, reason=PaymentEligibilityReasons.PAYOUT_CARD_NOT_SETUP
            )
        # sort payout cards by created_at
        payout_cards.sort(key=lambda payout_card: payout_card.created_at, reverse=True)
        # payout cards are already sorted by id desc
        latest_payout_card = payout_cards[0]
        delta = datetime.now().timestamp() - datetime.timestamp(
            latest_payout_card.created_at.replace(tzinfo=pytz.utc)
        )
        if delta < InstantPayoutCardChangeBlockTimeInDays * 24 * 3600:
            # populate details to response to be compatible with DSJ
            details = {
                "num_days_blocked": InstantPayoutCardChangeBlockTimeInDays,
                "cards_changed": [latest_payout_card],
            }

            return PayoutCardEligibility(
                eligible=False,
                reason=PaymentEligibilityReasons.PAYOUT_CARD_CHANGED_RECENTLY,
                details=details,
            )
        return PayoutCardEligibility(eligible=True)

    def _handle_exception(
        self, internal_exec: Exception
    ) -> Union[PaymentError, PayoutCardEligibility]:
        raise


class CheckPayoutAccountBalance(
    AsyncOperation[EligibilityCheckRequest, BalanceEligibility]
):
    """Instant Payout Balance Eligibility Check.

    Check available balance status
    """

    def __init__(
        self,
        request: EligibilityCheckRequest,
        transaction_repo: TransactionRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.payout_account_id = request.payout_account_id
        self.transaction_repo = transaction_repo

    async def _execute(self) -> BalanceEligibility:
        # get available balance by payout account id
        transactions = await self.transaction_repo.get_unpaid_transaction_by_payout_account_id_without_limit(
            payout_account_id=self.payout_account_id
        )
        balance = sum([transaction.amount for transaction in transactions])

        if balance < InstantPayoutFees.STANDARD_FEE:
            return BalanceEligibility(
                eligible=False,
                reason=PaymentEligibilityReasons.INSUFFICIENT_BALANCE,
                balance=balance,
            )

        return BalanceEligibility(eligible=True, balance=balance)

    def _handle_exception(
        self, internal_exec: Exception
    ) -> Union[PaymentError, BalanceEligibility]:
        raise


class CheckInstantPayoutDailyLimit(
    (AsyncOperation[EligibilityCheckRequest, InstantPayoutDailyLimitEligibility])
):
    """Instant Payout Daily Limit Check.

    Check if there is already instant payout initiated. The time to query is based on Dx/Mx's own timezone. An initiated
    instant payout status includes new, pending, paid, failed. Error status instant payout is not included.
    """

    def __init__(
        self,
        request: EligibilityCheckRequest,
        payout_repo: PayoutRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.payout_account_id = request.payout_account_id
        self.created_after = request.created_after
        self.payout_repo = payout_repo

    async def _execute(self) -> InstantPayoutDailyLimitEligibility:
        instant_payouts = await self.payout_repo.list_payout_by_payout_account_id(
            payout_account_id=self.payout_account_id,
            statuses=InstantPayoutDailyLimitCheckStatuses,
            start_time=self.created_after,
            offset=0,
        )

        if instant_payouts:
            return InstantPayoutDailyLimitEligibility(
                eligible=False, reason=PaymentEligibilityReasons.ALREADY_PAID_OUT_TODAY
            )
        return InstantPayoutDailyLimitEligibility(eligible=True)

    def _handle_exception(
        self, internal_exec: Exception
    ) -> Union[PaymentError, InstantPayoutDailyLimitEligibility]:
        raise
