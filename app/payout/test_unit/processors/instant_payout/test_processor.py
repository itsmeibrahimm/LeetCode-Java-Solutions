import json
from datetime import datetime

import pytest
from asynctest import MagicMock, mock

from app.commons.core.errors import DBConnectionError
from app.commons.types import Currency
from app.payout.core.instant_payout.models import (
    EligibilityCheckRequest,
    PayoutAccountEligibility,
    PayoutCardEligibility,
    BalanceEligibility,
    InstantPayoutDailyLimitEligibility,
    InternalPaymentEligibility,
    InstantPayoutFees,
    PaymentEligibilityReasons,
    InstantPayoutCardChangeBlockTimeInDays,
    payment_eligibility_reason_details,
)
from app.payout.core.instant_payout.processor import InstantPayoutProcessors


class TestInstantPayoutProcessors:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mock_check_payout_account,
        mock_check_payout_card,
        mock_check_balance,
        mock_check_daily_limit,
    ):
        self.instant_payout_processor = InstantPayoutProcessors(
            logger=MagicMock(),
            payout_account_repo=MagicMock(),
            payout_card_repo=MagicMock(),
            payout_method_repo=MagicMock(),
            payout_repo=MagicMock(),
            stripe_managed_account_transfer_repo=MagicMock(),
            stripe_payout_request_repo=MagicMock(),
            transaction_repo=MagicMock(),
            stripe=MagicMock(),
            payment_lock_manager=MagicMock(),
        )
        self.request = EligibilityCheckRequest(
            payout_account_id=123, created_after=datetime.utcnow()
        )

    async def test_check_instant_payout_eligible(
        self,
        mock_check_payout_account,
        mock_check_payout_card,
        mock_check_balance,
        mock_check_daily_limit,
    ):
        currency = Currency.USD
        balance = 300
        mock_check_payout_account.return_value = PayoutAccountEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=True,
            currency=currency,
            fee=InstantPayoutFees.STANDARD_FEE,
        )
        mock_check_payout_card.return_value = PayoutCardEligibility(
            payout_account_id=self.request.payout_account_id, eligible=True
        )
        mock_check_balance.return_value = BalanceEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=True,
            balance=balance,
        )
        mock_check_daily_limit.return_value = InstantPayoutDailyLimitEligibility(
            payout_account_id=self.request.payout_account_id, eligible=True
        )

        assert await self.instant_payout_processor.check_instant_payout_eligibility(
            self.request
        ) == InternalPaymentEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=True,
            currency=currency,
            balance=balance,
            fee=InstantPayoutFees.STANDARD_FEE,
        )

    async def test_check_instant_payout_not_eligible_due_to_payout_account_not_exist(
        self, mock_check_payout_account
    ):
        mock_check_payout_account.return_value = PayoutAccountEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_ACCOUNT_NOT_EXIST,
            details=payment_eligibility_reason_details[
                PaymentEligibilityReasons.PAYOUT_ACCOUNT_NOT_EXIST
            ],
        )

        assert await self.instant_payout_processor.check_instant_payout_eligibility(
            self.request
        ) == InternalPaymentEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_ACCOUNT_NOT_EXIST,
            details=payment_eligibility_reason_details[
                PaymentEligibilityReasons.PAYOUT_ACCOUNT_NOT_EXIST
            ],
        )

    async def test_check_instant_payout_not_eligible_due_to_payout_pgp_account_not_setup(
        self, mock_check_payout_account
    ):
        mock_check_payout_account.return_value = PayoutAccountEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_SETUP,
            details=payment_eligibility_reason_details[
                PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_SETUP
            ],
            fee=InstantPayoutFees.STANDARD_FEE,
        )

        assert await self.instant_payout_processor.check_instant_payout_eligibility(
            self.request
        ) == InternalPaymentEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_SETUP,
            details=payment_eligibility_reason_details[
                PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_SETUP
            ],
            fee=InstantPayoutFees.STANDARD_FEE,
        )

    async def test_check_instant_payout_not_eligible_due_to_payout_card(
        self, mock_check_payout_account, mock_check_payout_card
    ):
        mock_check_payout_account.return_value = PayoutAccountEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=True,
            fee=InstantPayoutFees.STANDARD_FEE,
            currency=Currency.USD,
        )
        details = {
            "num_days_blocked": InstantPayoutCardChangeBlockTimeInDays,
            "cards_changed": [{}],
        }
        mock_check_payout_card.return_value = PayoutCardEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_CARD_CHANGED_RECENTLY,
            details=json.dumps(details, default=str),
        )

        assert await self.instant_payout_processor.check_instant_payout_eligibility(
            self.request
        ) == InternalPaymentEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_CARD_CHANGED_RECENTLY,
            fee=InstantPayoutFees.STANDARD_FEE,
            details=json.dumps(details, default=str),
        )

    async def test_check_instant_payout_not_eligible_due_to_balance(
        self, mock_check_payout_account, mock_check_payout_card, mock_check_balance
    ):
        mock_check_payout_account.return_value = PayoutAccountEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=True,
            fee=InstantPayoutFees.STANDARD_FEE,
            currency=Currency.USD,
        )
        mock_check_payout_card.return_value = PayoutCardEligibility(
            payout_account_id=self.request.payout_account_id, eligible=True
        )

        balance = 100
        mock_check_balance.return_value = BalanceEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=False,
            reason=PaymentEligibilityReasons.INSUFFICIENT_BALANCE,
            details=payment_eligibility_reason_details[
                PaymentEligibilityReasons.INSUFFICIENT_BALANCE
            ],
            balance=balance,
        )

        assert await self.instant_payout_processor.check_instant_payout_eligibility(
            self.request
        ) == InternalPaymentEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=False,
            reason=PaymentEligibilityReasons.INSUFFICIENT_BALANCE,
            details=payment_eligibility_reason_details[
                PaymentEligibilityReasons.INSUFFICIENT_BALANCE
            ],
            balance=balance,
            currency=Currency.USD,
            fee=InstantPayoutFees.STANDARD_FEE,
        )

    async def test_check_instant_payout_not_eligible_due_to_daily_limit(
        self,
        mock_check_payout_account,
        mock_check_payout_card,
        mock_check_balance,
        mock_check_daily_limit,
    ):
        mock_check_payout_account.return_value = PayoutAccountEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=True,
            fee=InstantPayoutFees.STANDARD_FEE,
            currency=Currency.USD,
        )
        mock_check_payout_card.return_value = PayoutCardEligibility(
            payout_account_id=self.request.payout_account_id, eligible=True
        )

        balance = 100
        mock_check_balance.return_value = BalanceEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=True,
            balance=balance,
        )

        mock_check_daily_limit.return_value = InstantPayoutDailyLimitEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=False,
            reason=PaymentEligibilityReasons.ALREADY_PAID_OUT_TODAY,
            details=payment_eligibility_reason_details[
                PaymentEligibilityReasons.ALREADY_PAID_OUT_TODAY
            ],
        )

        assert await self.instant_payout_processor.check_instant_payout_eligibility(
            self.request
        ) == InternalPaymentEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=False,
            reason=PaymentEligibilityReasons.ALREADY_PAID_OUT_TODAY,
            details=payment_eligibility_reason_details[
                PaymentEligibilityReasons.ALREADY_PAID_OUT_TODAY
            ],
            balance=balance,
            currency=Currency.USD,
            fee=InstantPayoutFees.STANDARD_FEE,
        )

    async def test_check_instant_payout_raise_exception(
        self, mock_check_payout_account
    ):
        mock_check_payout_account.side_effect = DBConnectionError("some error")

        with pytest.raises(DBConnectionError):
            await self.instant_payout_processor.check_instant_payout_eligibility(
                self.request
            )


@pytest.fixture
def mock_check_payout_account():
    with mock.patch(
        "app.payout.core.instant_payout.processor.CheckPayoutAccount.execute"
    ) as mock_check_payout_account:
        yield mock_check_payout_account


@pytest.fixture
def mock_check_payout_card():
    with mock.patch(
        "app.payout.core.instant_payout.processor.CheckPayoutCard.execute"
    ) as mock_check_payout_card:
        yield mock_check_payout_card


@pytest.fixture
def mock_check_balance():
    with mock.patch(
        "app.payout.core.instant_payout.processor.CheckPayoutAccountBalance.execute"
    ) as mock_check_balance:
        yield mock_check_balance


@pytest.fixture
def mock_check_daily_limit():
    with mock.patch(
        "app.payout.core.instant_payout.processor.CheckInstantPayoutDailyLimit.execute"
    ) as mock_check_daily_limit:
        yield mock_check_daily_limit
