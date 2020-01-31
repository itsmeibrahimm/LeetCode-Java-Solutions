import asyncio
import json
from datetime import datetime
from unittest.mock import Mock

import pytest
import pytest_mock
import pytz
from asynctest import MagicMock, mock

from app.commons.core.errors import DBConnectionError, PaymentDBLockReleaseError
from app.commons.lock.models import LockInternal, LockStatus
from app.commons.lock.payment_db_lock import PaymentDBLock
from app.commons.operational_flags import ENABLED_PAYMENT_DB_LOCK_FOR_PAYOUT
from app.commons.types import Currency
from app.conftest import RuntimeSetter
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
    VerifyTransactionsResponse,
    SMABalance,
    SubmitInstantPayoutResponse,
    CreateAndSubmitInstantPayoutRequest,
    CreateAndSubmitInstantPayoutResponse,
    CreatePayoutsResponse,
    PayoutCardResponse,
)
from app.payout.core.instant_payout.processor import InstantPayoutProcessors
from app.payout.repository.maindb.model.payment_account import PaymentAccount
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
)


@pytest.mark.asyncio
class TestInstantPayoutProcessors:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        payment_account_repo,
        payout_lock_repo,
        payout_repo,
        mock_check_payout_account,
        mock_check_payout_card,
        mock_check_balance,
        mock_check_daily_limit,
    ):
        self.mock_logger = MagicMock()
        self.instant_payout_processor = InstantPayoutProcessors(
            logger=self.mock_logger,
            payout_account_repo=payment_account_repo,
            payout_card_repo=MagicMock(),
            payout_method_repo=MagicMock(),
            payout_repo=payout_repo,
            stripe_managed_account_transfer_repo=MagicMock(),
            stripe_payout_request_repo=MagicMock(),
            transaction_repo=MagicMock(),
            stripe=MagicMock(),
            payment_lock_manager=MagicMock(),
            payout_lock_repo=payout_lock_repo,
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

    async def test_create_and_submit_instant_payout_enable_db_lock(
        self,
        mocker: pytest_mock.MockFixture,
        mock_check_payout_account,
        mock_get_payout_card,
        mock_get_sma,
        mock_verify_transactions,
        mock_create_payout_response,
        mock_check_sma_balance,
        mock_submit_instant_payout,
        runtime_setter: RuntimeSetter,
        payout_lock_repo,
    ):
        currency = Currency.USD
        mocked_payout_account_id = 1
        mocked_payout_amount = 2000
        mocked_stripe_payout_id = "test_stripe_payout_id"
        mocked_payout_id = 1
        mocked_payout_card_id = 1
        mocked_stripe_card_id = "test_stripe_card_id"
        mocked_transaction_list = [1, 2, 3]
        mock_check_payout_account.return_value = PayoutAccountEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=True,
            currency=currency,
            fee=InstantPayoutFees.STANDARD_FEE,
        )
        mock_get_payout_card.return_value = PayoutCardResponse(
            payout_card_id=mocked_payout_card_id, stripe_card_id=mocked_stripe_card_id
        )

        # mock get_payment_account_by_id
        @asyncio.coroutine
        def mock_get_payment_account(*args, **kwargs):
            return PaymentAccount(
                id=mocked_payout_account_id,
                statement_descriptor="test_statement_descriptor",
                account_id=1,
                account_type="stripe_managed_account",
            )

        mock_get_payment_account_by_id: Mock = mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_payment_account_by_id",
            side_effect=mock_get_payment_account,
        )

        mock_get_sma.return_value = StripeManagedAccount(
            id=1, country_shortname="US", stripe_id="test_stripe_id"
        )
        mock_verify_transactions.return_value = VerifyTransactionsResponse(
            transaction_ids=mocked_transaction_list
        )

        # mock feature_flag to enable payment db lock
        data = {
            "enable_all": False,
            "white_list": [mocked_payout_account_id],
            "bucket": 0,
        }
        runtime_setter.set(ENABLED_PAYMENT_DB_LOCK_FOR_PAYOUT, data)

        # mock payment db lock
        mocked_lock_id = "test_db_lock_for_instant_payout"

        @asyncio.coroutine
        def mock_payment_db_lock(*args, **kwargs):
            return PaymentDBLock(payout_lock_repo, mocked_lock_id)

        mocker.patch(
            "app.commons.lock.payment_db_lock.PaymentDBLock",
            side_effect=mock_payment_db_lock,
        )

        @asyncio.coroutine
        def mock_lock_internal(*args, **kwargs):
            return LockInternal(
                lock_id=mocked_lock_id,
                status=LockStatus.LOCKED,
                lock_timestamp=datetime.utcnow(),
                ttl_sec=30,
            )

        mock_lock: Mock = mocker.patch(
            "app.payout.repository.paymentdb.payout_lock.PayoutLockRepository.lock",
            side_effect=mock_lock_internal,
        )

        @asyncio.coroutine
        def mock_unlock_internal(*args, **kwargs):
            return LockInternal(
                lock_id=mocked_lock_id,
                status=LockStatus.OPEN,
                lock_timestamp=datetime.utcnow(),
                ttl_sec=30,
            )

        mock_unlock: Mock = mocker.patch(
            "app.payout.repository.paymentdb.payout_lock.PayoutLockRepository.unlock",
            side_effect=mock_unlock_internal,
        )
        mocked_created_at = datetime.utcnow().replace(tzinfo=pytz.UTC)
        mock_create_payout_response.return_value = CreatePayoutsResponse(
            payout_id=mocked_payout_id,
            amount=mocked_payout_amount,
            fee=InstantPayoutFees.STANDARD_FEE,
            created_at=mocked_created_at,
        )

        mock_check_sma_balance.return_value = SMABalance(balance=900000)
        mock_submit_instant_payout.return_value = SubmitInstantPayoutResponse(
            stripe_payout_id=mocked_stripe_payout_id,
            stripe_object="stripe_payout",
            status="paid",
            amount=mocked_payout_amount,
            currency=Currency.USD,
            destination="test_destination_account",
        )

        create_and_submit_instant_payout_request = CreateAndSubmitInstantPayoutRequest(
            payout_account_id=mocked_payout_account_id,
            amount=mocked_payout_amount,
            currency=Currency.USD,
            card=None,
        )

        assert await self.instant_payout_processor.create_and_submit_instant_payout(
            create_and_submit_instant_payout_request
        ) == CreateAndSubmitInstantPayoutResponse(
            payout_account_id=mocked_payout_account_id,
            payout_id=mocked_payout_id,
            amount=mocked_payout_amount,
            currency=Currency.USD,
            fee=InstantPayoutFees.STANDARD_FEE,
            status="paid",
            card="test_destination_account",
            created_at=mocked_created_at,
        )
        assert mock_get_payment_account_by_id.called
        assert mock_lock.called
        assert mock_unlock.called
        assert self.mock_logger.info.call_count == 7

    async def test_create_and_submit_instant_payout_enable_db_lock_raise_exception(
        self,
        mocker: pytest_mock.MockFixture,
        mock_check_payout_account,
        mock_get_payout_card,
        mock_get_sma,
        mock_verify_transactions,
        mock_create_payout_response,
        mock_check_sma_balance,
        mock_submit_instant_payout,
        runtime_setter: RuntimeSetter,
        payout_lock_repo,
    ):
        currency = Currency.USD
        mocked_payout_account_id = 1
        mocked_payout_amount = 2000
        mocked_stripe_payout_id = "test_stripe_payout_id"
        mocked_payout_id = 1
        mocked_payout_card_id = 1
        mocked_stripe_card_id = "test_stripe_card_id"
        mocked_transaction_list = [1, 2, 3]
        mock_check_payout_account.return_value = PayoutAccountEligibility(
            payout_account_id=self.request.payout_account_id,
            eligible=True,
            currency=currency,
            fee=InstantPayoutFees.STANDARD_FEE,
        )
        mock_get_payout_card.return_value = PayoutCardResponse(
            payout_card_id=mocked_payout_card_id, stripe_card_id=mocked_stripe_card_id
        )

        # mock get_payment_account_by_id
        @asyncio.coroutine
        def mock_get_payment_account(*args, **kwargs):
            return PaymentAccount(
                id=mocked_payout_account_id,
                statement_descriptor="test_statement_descriptor",
                account_id=1,
                account_type="stripe_managed_account",
            )

        mock_get_payment_account_by_id: Mock = mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_payment_account_by_id",
            side_effect=mock_get_payment_account,
        )

        mock_get_sma.return_value = StripeManagedAccount(
            id=1, country_shortname="US", stripe_id="test_stripe_id"
        )
        mock_verify_transactions.return_value = VerifyTransactionsResponse(
            transaction_ids=mocked_transaction_list
        )

        # mock feature_flag to enable payment db lock
        data = {
            "enable_all": False,
            "white_list": [mocked_payout_account_id],
            "bucket": 0,
        }
        runtime_setter.set(ENABLED_PAYMENT_DB_LOCK_FOR_PAYOUT, data)

        # mock payment db lock
        mocked_lock_id = "test_db_lock_for_instant_payout"

        @asyncio.coroutine
        def mock_payment_db_lock(*args, **kwargs):
            return PaymentDBLock(payout_lock_repo, mocked_lock_id)

        mocker.patch(
            "app.commons.lock.payment_db_lock.PaymentDBLock",
            side_effect=mock_payment_db_lock,
        )

        @asyncio.coroutine
        def mock_lock_internal(*args, **kwargs):
            return None

        mock_lock: Mock = mocker.patch(
            "app.payout.repository.paymentdb.payout_lock.PayoutLockRepository.lock",
            side_effect=mock_lock_internal,
        )

        @asyncio.coroutine
        def mock_unlock_internal(*args, **kwargs):
            return LockInternal(
                lock_id=mocked_lock_id,
                status=LockStatus.OPEN,
                lock_timestamp=datetime.utcnow(),
                ttl_sec=30,
            )

        mock_unlock: Mock = mocker.patch(
            "app.payout.repository.paymentdb.payout_lock.PayoutLockRepository.unlock",
            side_effect=mock_unlock_internal,
        )
        mocked_created_at = datetime.utcnow().replace(tzinfo=pytz.UTC)
        mock_create_payout_response.return_value = CreatePayoutsResponse(
            payout_id=mocked_payout_id,
            amount=mocked_payout_amount,
            fee=InstantPayoutFees.STANDARD_FEE,
            created_at=mocked_created_at,
        )

        mock_check_sma_balance.return_value = SMABalance(balance=900000)
        mock_submit_instant_payout.return_value = SubmitInstantPayoutResponse(
            stripe_payout_id=mocked_stripe_payout_id,
            stripe_object="stripe_payout",
            status="paid",
            amount=mocked_payout_amount,
            currency=Currency.USD,
            destination="test_destination_account",
        )

        create_and_submit_instant_payout_request = CreateAndSubmitInstantPayoutRequest(
            payout_account_id=mocked_payout_account_id,
            amount=mocked_payout_amount,
            currency=Currency.USD,
            card=None,
        )

        with pytest.raises(PaymentDBLockReleaseError):
            assert await self.instant_payout_processor.create_and_submit_instant_payout(
                create_and_submit_instant_payout_request
            ) == CreateAndSubmitInstantPayoutResponse(
                payout_account_id=mocked_payout_account_id,
                payout_id=mocked_payout_id,
                amount=mocked_payout_amount,
                currency=Currency.USD,
                fee=InstantPayoutFees.STANDARD_FEE,
                status="paid",
                card="test_destination_account",
                created_at=mocked_created_at,
            )
        assert mock_get_payment_account_by_id.called
        assert mock_lock.called
        assert not mock_unlock.called


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


@pytest.fixture
def mock_get_sma():
    with mock.patch(
        "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_stripe_managed_account_by_id"
    ) as mock_get_sma:
        yield mock_get_sma


@pytest.fixture
def mock_get_payout_card():
    with mock.patch(
        "app.payout.core.instant_payout.processor.GetPayoutCard.execute"
    ) as mock_get_payout_card:
        yield mock_get_payout_card


@pytest.fixture
def mock_verify_transactions():
    with mock.patch(
        "app.payout.core.instant_payout.processor.VerifyTransactions.execute"
    ) as mock_verify_transactions:
        yield mock_verify_transactions


@pytest.fixture
def mock_check_sma_balance():
    with mock.patch(
        "app.payout.core.instant_payout.processor.CheckSMABalance.execute"
    ) as mock_check_sma_balance:
        yield mock_check_sma_balance


@pytest.fixture
def mock_submit_instant_payout():
    with mock.patch(
        "app.payout.core.instant_payout.processor.SubmitInstantPayout.execute"
    ) as mock_submit_instant_payout:
        yield mock_submit_instant_payout


@pytest.fixture
def mock_create_payout_response():
    with mock.patch(
        "app.payout.repository.bankdb.payout.PayoutRepository.create_payout_and_attach_to_transactions"
    ) as mock_create_payout_response:
        yield mock_create_payout_response
