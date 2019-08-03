import pytest

from app.commons.database.model import Database
from app.payout.repository.maindb.payment_account import (
    PaymentAccountWritable,
    PaymentAccountRepository,
)


class TestPaymentAccountRepository:
    pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

    async def test_create(self, payout_maindb: Database):
        repo = PaymentAccountRepository(database=payout_maindb)
        payment_account = PaymentAccountWritable(
            account_type="some_type",
            account_id=123,
            statement_descriptor="my account",
            entity="dasher",
        )

        account = await repo.create_payment_account(payment_account)
        assert account.id, "account is created, assigned an ID"

        assert account == await repo.get_payment_account_by_id(
            account.id
        ), "retrieved account matches"
