import pytest
from app.payout.domain.payout_account.models import PayoutAccount
from app.payout.domain.payout_account.payment_account_repository import (
    PayoutAccountRepository,
)


class TestPaymentAccountRepository:
    pytestmark = pytest.mark.asyncio

    @pytest.mark.skip(reason="database connection not available")
    async def test_create(self, payout_maindb):
        repo = PayoutAccountRepository(payout_maindb)
        create_payout_account = PayoutAccount(
            account_type="some_type",
            account_id="acct_abc123",
            statement_descriptor="my account",
        )

        account = await repo.create_payout_account(create_payout_account)
        assert account.id, "account is created, assigned an ID"

        assert account == repo.get_payout_account_by_id(
            account.id
        ), "retrieved account matches"
