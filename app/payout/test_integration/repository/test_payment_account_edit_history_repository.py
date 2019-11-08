from datetime import timedelta

import pytest
from app.commons.database.infra import DB
from app.payout.repository.bankdb.model.payment_account_edit_history import (
    PaymentAccountEditHistoryCreate,
    PaymentAccountEditHistory,
)
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepository,
)
from app.payout import models
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import prepare_and_insert_stripe_managed_account


class TestPaymentAccountEditHistoryRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payment_account_edit_history_repo(
        self, payout_bankdb: DB
    ) -> PaymentAccountEditHistoryRepository:
        return PaymentAccountEditHistoryRepository(database=payout_bankdb)

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    async def created_payment_edit_history(
        self,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        new_bank_name = "new_bank_name"
        new_bank_last4 = "new_bank_last4"
        new_fingerprint = "new_fingerprint"
        old_bank_name = "old_bank_name"
        old_bank_last4 = "old_bank_last4"
        old_fingerprint = "old_fingerprint"
        stripe_managed_account = await prepare_and_insert_stripe_managed_account(
            payment_account_repo
        )
        data = PaymentAccountEditHistoryCreate(
            account_type=models.AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT,
            account_id=stripe_managed_account.id,
            new_bank_name=new_bank_name,
            new_bank_last4=new_bank_last4,
            new_fingerprint=new_fingerprint,
            payment_account_id=1,
            owner_type=None,
            owner_id=None,
            old_bank_name=old_bank_name,
            old_bank_last4=old_bank_last4,
            old_fingerprint=old_fingerprint,
            login_as_user_id=None,
            user_id=None,
            device_id=None,
            ip=None,
        )
        created_record = await payment_account_edit_history_repo.record_bank_update(
            data=data
        )
        assert created_record
        assert created_record.id
        assert created_record.new_fingerprint == new_fingerprint
        return created_record

    async def test_get_most_recent_bank_update(
        self,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
        created_payment_edit_history: PaymentAccountEditHistory,
    ):
        assert created_payment_edit_history
        assert created_payment_edit_history.payment_account_id
        retrieved_payment_edit_history = await payment_account_edit_history_repo.get_most_recent_bank_update(
            payment_account_id=created_payment_edit_history.payment_account_id,
            within_last_timedelta=timedelta(days=2),
        )
        assert retrieved_payment_edit_history
        assert retrieved_payment_edit_history == created_payment_edit_history
