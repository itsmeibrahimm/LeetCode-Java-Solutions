from datetime import timedelta

import pytest
from app.commons.database.infra import DB
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepository,
)


class TestPaymentAccountEditHistoryRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payment_account_edit_history_repo(
        self, payout_bankdb: DB
    ) -> PaymentAccountEditHistoryRepository:
        return PaymentAccountEditHistoryRepository(database=payout_bankdb)

    @pytest.mark.skip("no create function for now")
    async def test_get_most_recent_bank_update(
        self, payment_account_edit_history_repo: PaymentAccountEditHistoryRepository
    ):
        retrieved_payment_edit_history = await payment_account_edit_history_repo.get_most_recent_bank_update(
            payment_account_id=234, within_last_timedelta=timedelta(days=2)
        )
        assert retrieved_payment_edit_history
        assert retrieved_payment_edit_history.id == 1
