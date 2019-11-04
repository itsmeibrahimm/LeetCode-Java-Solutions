import uuid
from datetime import datetime, timedelta

import pytest
from asynctest import mock, CoroutineMock

from app.commons.core.errors import DBConnectionError, DBIntegrityError
from app.commons.types import CountryCode, Currency
from app.payout.core.instant_payout.models import (
    EligibilityCheckRequest,
    PayoutAccountEligibility,
    PaymentEligibilityReasons,
    PayoutCardEligibility,
    BalanceEligibility,
    InstantPayoutDailyLimitEligibility,
    InstantPayoutFees,
    InstantPayoutCardChangeBlockTimeInDays,
)
from app.payout.core.instant_payout.processors.check_eligibility import (
    CheckPayoutAccount,
    CheckPayoutCard,
    CheckPayoutAccountBalance,
    CheckInstantPayoutDailyLimit,
)
from app.payout.models import PayoutAccountTargetType, PgpAccountType
from app.payout.repository.bankdb.model.payout import Payout
from app.payout.repository.bankdb.model.payout_card import PayoutCard
from app.payout.repository.bankdb.model.payout_method import PayoutMethod
from app.payout.repository.maindb.model.payment_account import PaymentAccount
from app.payout.repository.bankdb.model.transaction import TransactionDBEntity
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
)


class TestCheckPayoutAccount:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(self, mock_payout_account_repo):
        self.payout_account = PaymentAccount(
            id=111,
            entity=PayoutAccountTargetType.DASHER,
            account_id=321,
            account_type=PgpAccountType.STRIPE,
            statement_descriptor="",
        )
        self.pgp_account = StripeManagedAccount(
            id=self.payout_account.account_id,
            country_shortname=CountryCode.US,
            verification_disabled_reason=None,
            stripe_id="acct_xxx",
        )
        mock_payout_account_repo.get_payment_account_by_id = CoroutineMock()
        mock_payout_account_repo.get_stripe_managed_account_by_id = CoroutineMock()
        self.payout_account_check = CheckPayoutAccount(
            EligibilityCheckRequest(payout_account_id=111), mock_payout_account_repo
        )

    async def test_eligible(self, mock_payout_account_repo):
        mock_payout_account_repo.get_payment_account_by_id.return_value = (
            self.payout_account
        )
        mock_payout_account_repo.get_stripe_managed_account_by_id.return_value = (
            self.pgp_account
        )
        assert await self.payout_account_check.execute() == PayoutAccountEligibility(
            eligible=True, currency=Currency.USD, fee=InstantPayoutFees.STANDARD_FEE
        )

    async def test_not_eligible_due_to_payout_account_not_exist(
        self, mock_payout_account_repo
    ):
        mock_payout_account_repo.get_payment_account_by_id.return_value = None
        # PayoutAccountEligibility should not have fee
        assert await self.payout_account_check.execute() == PayoutAccountEligibility(
            eligible=False, reason=PaymentEligibilityReasons.PAYOUT_ACCOUNT_NOT_EXIST
        )

    async def test_not_eligible_due_to_payout_account_entity_not_supported(
        self, mock_payout_account_repo
    ):
        mock_payout_account_repo.get_payment_account_by_id.return_value = self.payout_account.copy(
            deep=True, update={"entity": PayoutAccountTargetType.STORE}
        )

        assert await self.payout_account_check.execute() == PayoutAccountEligibility(
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_ACCOUNT_TYPE_NOT_SUPPORTED,
            fee=InstantPayoutFees.STANDARD_FEE,
        )

    async def test_not_eligible_due_to_pgp_account_not_setup(
        self, mock_payout_account_repo
    ):
        # account_id is None
        mock_payout_account_repo.get_payment_account_by_id.return_value = self.payout_account.copy(
            deep=True, update={"account_id": None}
        )

        assert await self.payout_account_check.execute() == PayoutAccountEligibility(
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_SETUP,
            fee=InstantPayoutFees.STANDARD_FEE,
        )

        # account type is not stripe_managed_account
        mock_payout_account_repo.get_payment_account_by_id.return_value = self.payout_account.copy(
            deep=True, update={"account_type": "unknown types"}
        )
        assert await self.payout_account_check.execute() == PayoutAccountEligibility(
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_SETUP,
            fee=InstantPayoutFees.STANDARD_FEE,
        )

    async def test_not_eligible_due_to_pgp_account_not_exist(
        self, mock_payout_account_repo
    ):
        mock_payout_account_repo.get_payment_account_by_id.return_value = (
            self.payout_account
        )
        mock_payout_account_repo.get_stripe_managed_account_by_id.return_value = None
        assert await self.payout_account_check.execute() == PayoutAccountEligibility(
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_EXIST,
            fee=InstantPayoutFees.STANDARD_FEE,
        )

    async def test_not_eligible_due_to_pgp_account_country_not_supported(
        self, mock_payout_account_repo
    ):
        mock_payout_account_repo.get_payment_account_by_id.return_value = (
            self.payout_account
        )
        mock_payout_account_repo.get_stripe_managed_account_by_id.return_value = self.pgp_account.copy(
            deep=True, update={"country_shortname": CountryCode.CA}
        )
        assert await self.payout_account_check.execute() == PayoutAccountEligibility(
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_ACCOUNT_COUNTRY_NOT_SUPPORTED,
            fee=InstantPayoutFees.STANDARD_FEE,
        )

    async def test_not_eligible_due_to_pgp_account_not_verified(
        self, mock_payout_account_repo
    ):
        mock_payout_account_repo.get_payment_account_by_id.return_value = (
            self.payout_account
        )
        mock_payout_account_repo.get_stripe_managed_account_by_id.return_value = self.pgp_account.copy(
            deep=True, update={"verification_disabled_reason": "some reason"}
        )
        assert await self.payout_account_check.execute() == PayoutAccountEligibility(
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_PGP_ACCOUNT_NOT_VERIFIED,
            fee=InstantPayoutFees.STANDARD_FEE,
        )

    async def test_raise_db_error_when_get_payout_account_error(
        self, mock_payout_account_repo
    ):
        mock_payout_account_repo.get_payment_account_by_id.side_effect = DBConnectionError(
            "some error"
        )
        with pytest.raises(DBConnectionError):
            await self.payout_account_check.execute()

    async def test_raise_db_error_when_get_pgp_account_error(
        self, mock_payout_account_repo
    ):
        mock_payout_account_repo.get_payment_account_by_id.return_value = (
            self.payout_account
        )
        mock_payout_account_repo.get_stripe_managed_account_by_id.side_effect = DBConnectionError(
            "some error"
        )
        with pytest.raises(DBConnectionError):
            await self.payout_account_check.execute()


class TestCheckPayoutCard:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(self, mock_payout_method_repo, mock_payout_card_repo):
        created_at = datetime.utcnow() - timedelta(days=8)
        updated_at = datetime.utcnow() - timedelta(days=8)
        token = str(uuid.uuid4())
        self.payout_method = PayoutMethod(
            id=111,
            type="card",
            currency=Currency.USD,
            country=CountryCode.US,
            payment_account_id=123,
            token=token,
            created_at=created_at,
            updated_at=updated_at,
        )
        self.payout_card = PayoutCard(
            id=self.payout_method.id,
            stripe_card_id="card_xxx",
            last4="1234",
            brand="visa",
            exp_month=11,
            exp_year=29,
            created_at=created_at,
            updated_at=updated_at,
        )
        mock_payout_method_repo.list_payout_methods_by_payout_account_id = (
            CoroutineMock()
        )
        mock_payout_card_repo.list_payout_cards_by_ids = CoroutineMock()
        self.payout_card_check = CheckPayoutCard(
            EligibilityCheckRequest(payout_account_id=123),
            mock_payout_method_repo,
            mock_payout_card_repo,
        )

    async def test_eligible(self, mock_payout_method_repo, mock_payout_card_repo):
        mock_payout_method_repo.list_payout_methods_by_payout_account_id.return_value = [
            self.payout_method
        ]
        mock_payout_card_repo.list_payout_cards_by_ids.return_value = [self.payout_card]
        assert await self.payout_card_check.execute() == PayoutCardEligibility(
            eligible=True
        )

    async def test_not_eligible_due_to_payout_card_not_exist(
        self, mock_payout_method_repo, mock_payout_card_repo
    ):
        mock_payout_method_repo.list_payout_methods_by_payout_account_id.return_value = [
            self.payout_method
        ]
        mock_payout_card_repo.list_payout_cards_by_ids.return_value = []
        assert await self.payout_card_check.execute() == PayoutCardEligibility(
            eligible=False, reason=PaymentEligibilityReasons.PAYOUT_CARD_NOT_SETUP
        )

    async def test_not_eligible_due_to_recently_changed_card(
        self, mock_payout_method_repo, mock_payout_card_repo
    ):
        mock_payout_method_repo.list_payout_methods_by_payout_account_id.return_value = [
            self.payout_method
        ]
        payout_card_copy = self.payout_card.copy(
            deep=True, update={"created_at": datetime.utcnow() - timedelta(days=6)}
        )
        mock_payout_card_repo.list_payout_cards_by_ids.return_value = [payout_card_copy]

        assert await self.payout_card_check.execute() == PayoutCardEligibility(
            eligible=False,
            reason=PaymentEligibilityReasons.PAYOUT_CARD_CHANGED_RECENTLY,
            details={
                "num_days_blocked": InstantPayoutCardChangeBlockTimeInDays,
                "cards_changed": [payout_card_copy],
            },
        )

    async def test_raise_db_error_when_get_payout_method_error(
        self, mock_payout_method_repo, mock_payout_card_repo
    ):
        mock_payout_method_repo.list_payout_methods_by_payout_account_id.side_effect = DBConnectionError(
            "some error"
        )
        with pytest.raises(DBConnectionError):
            await self.payout_card_check.execute()

    async def test_raise_db_error_when_get_payout_card_error(
        self, mock_payout_method_repo, mock_payout_card_repo
    ):
        mock_payout_method_repo.list_payout_methods_by_payout_account_id.return_value = [
            self.payout_method
        ]
        mock_payout_card_repo.list_payout_cards_by_ids.side_effect = DBIntegrityError(
            "some error"
        )
        with pytest.raises(DBIntegrityError):
            await self.payout_card_check.execute()


class TestCheckPayoutAccountBalance:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(self, mock_transaction_repo):
        self.transaction_1 = TransactionDBEntity(
            id=522,
            amount=100,
            payment_account_id=123,
            amount_paid=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.transaction_2 = TransactionDBEntity(
            id=524,
            amount=200,
            payment_account_id=123,
            amount_paid=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_transaction_repo.get_unpaid_transaction_by_payout_account_id_without_limit = (
            CoroutineMock()
        )
        self.payout_account_balance_check = CheckPayoutAccountBalance(
            EligibilityCheckRequest(payout_account_id=123), mock_transaction_repo
        )

    async def test_eligible(self, mock_transaction_repo):
        mock_transaction_repo.get_unpaid_transaction_by_payout_account_id_without_limit.return_value = [
            self.transaction_1,
            self.transaction_2,
        ]
        balance = self.transaction_1.amount + self.transaction_2.amount
        assert await self.payout_account_balance_check.execute() == BalanceEligibility(
            eligible=True, balance=balance
        )

    async def test_not_eligible_due_to_insufficient_balance(
        self, mock_transaction_repo
    ):
        mock_transaction_repo.get_unpaid_transaction_by_payout_account_id_without_limit.return_value = [
            self.transaction_1
        ]
        balance = self.transaction_1.amount
        assert await self.payout_account_balance_check.execute() == BalanceEligibility(
            eligible=False,
            reason=PaymentEligibilityReasons.INSUFFICIENT_BALANCE,
            balance=balance,
        )

    async def test_raise_db_error_when_get_unpaid_transaction_error(
        self, mock_transaction_repo
    ):
        mock_transaction_repo.get_unpaid_transaction_by_payout_account_id_without_limit.side_effect = DBConnectionError(
            "some error"
        )
        with pytest.raises(DBConnectionError):
            await self.payout_account_balance_check.execute()


class TestCheckInstantPayoutDailyLimit:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(self, mock_payout_repo):
        self.payout = Payout(
            id=111,
            amount=200,
            payment_account_id=123,
            status="active",
            currency=Currency.USD,
            fee=199,
            type="",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            idempotency_key="some-key",
            payout_method_id=123,
            transaction_ids=[123, 234],
            token="some-token",
        )
        mock_payout_repo.list_payout_by_payout_account_id = CoroutineMock()
        created_after = datetime.utcnow() - timedelta(days=1)
        self.instant_payout_daily_limit_check = CheckInstantPayoutDailyLimit(
            EligibilityCheckRequest(payout_account_id=123, created_after=created_after),
            mock_payout_repo,
        )

    async def test_eligible(self, mock_payout_repo):
        mock_payout_repo.list_payout_by_payout_account_id.return_value = []
        assert await self.instant_payout_daily_limit_check.execute() == InstantPayoutDailyLimitEligibility(
            eligible=True
        )

    async def test_not_eligible_due_to_already_paid_out(self, mock_payout_repo):
        mock_payout_repo.list_payout_by_payout_account_id.return_value = [self.payout]
        assert await self.instant_payout_daily_limit_check.execute() == InstantPayoutDailyLimitEligibility(
            eligible=False, reason=PaymentEligibilityReasons.ALREADY_PAID_OUT_TODAY
        )

    async def test_raise_db_error_when_list_payout_error(self, mock_payout_repo):
        mock_payout_repo.list_payout_by_payout_account_id.side_effect = DBIntegrityError(
            "some error"
        )
        with pytest.raises(DBIntegrityError):
            await self.instant_payout_daily_limit_check.execute()


@pytest.fixture
def mock_payout_account_repo():
    with mock.patch(
        "app.payout.repository.maindb.payment_account.PaymentAccountRepository"
    ) as mock_payout_account_repo:
        yield mock_payout_account_repo


@pytest.fixture
def mock_payout_method_repo():
    with mock.patch(
        "app.payout.repository.bankdb.payout_method.PayoutMethodRepository"
    ) as mock_payout_method_repo:
        yield mock_payout_method_repo


@pytest.fixture
def mock_payout_card_repo():
    with mock.patch(
        "app.payout.repository.bankdb.payout_card.PayoutCardRepository"
    ) as mock_payout_card_repo:
        yield mock_payout_card_repo


@pytest.fixture
def mock_transaction_repo():
    with mock.patch(
        "app.payout.repository.bankdb.transaction.TransactionRepository"
    ) as mock_transaction_repo:
        yield mock_transaction_repo


@pytest.fixture
def mock_payout_repo():
    with mock.patch(
        "app.payout.repository.bankdb.payout.PayoutRepository"
    ) as mock_payout_repo:
        yield mock_payout_repo
