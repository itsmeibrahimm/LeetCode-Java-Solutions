from datetime import timedelta, datetime

import pytest
from app.payout.models import BankUpdateHistoryOwnerType
from app.payout.repository.bankdb.model.payment_account_edit_history import (
    PaymentAccountEditHistoryCreate,
    PaymentAccountEditHistory,
)
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepository,
)
from app.payout import models
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_stripe_managed_account,
    prepare_and_insert_payment_account,
    prepare_and_insert_payment_account_edit_history,
)


class TestPaymentAccountEditHistoryRepository:
    pytestmark = [pytest.mark.asyncio]

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

    async def test_get_recent_bank_update_payment_account_ids_not_found(
        self, payment_account_edit_history_repo: PaymentAccountEditHistoryRepository
    ):
        payment_account_ids = await payment_account_edit_history_repo.get_recent_bank_update_payment_account_ids(
            last_bank_account_update_allowed_at=datetime.utcnow()
        )
        assert len(payment_account_ids) == 0

    async def test_get_recent_bank_update_payment_account_ids(
        self,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        timestamp = datetime.utcnow()
        original_payment_account_ids = await payment_account_edit_history_repo.get_recent_bank_update_payment_account_ids(
            last_bank_account_update_allowed_at=timestamp
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        await prepare_and_insert_payment_account_edit_history(
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            payment_account_id=payment_account.id,
        )

        new_payment_account_ids = await payment_account_edit_history_repo.get_recent_bank_update_payment_account_ids(
            last_bank_account_update_allowed_at=timestamp
        )
        assert len(new_payment_account_ids) - len(original_payment_account_ids) == 1
        assert (
            list(set(new_payment_account_ids) - set(original_payment_account_ids))[0]
            == payment_account.id
        )

    async def test_get_recent_bank_update_payment_account_ids_multiple_changes_return_distinct_ids(
        self,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        timestamp = datetime.utcnow()
        original_payment_account_ids = await payment_account_edit_history_repo.get_recent_bank_update_payment_account_ids(
            last_bank_account_update_allowed_at=timestamp
        )
        payment_account_a = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        await prepare_and_insert_payment_account_edit_history(
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            payment_account_id=payment_account_a.id,
        )
        await prepare_and_insert_payment_account_edit_history(
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            payment_account_id=payment_account_a.id,
        )

        payment_account_b = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        await prepare_and_insert_payment_account_edit_history(
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            payment_account_id=payment_account_b.id,
        )

        new_payment_account_ids = await payment_account_edit_history_repo.get_recent_bank_update_payment_account_ids(
            last_bank_account_update_allowed_at=timestamp
        )
        assert len(new_payment_account_ids) - len(original_payment_account_ids) == 2
        assert payment_account_a.id in list(
            set(new_payment_account_ids) - set(original_payment_account_ids)
        )
        assert payment_account_b.id in list(
            set(new_payment_account_ids) - set(original_payment_account_ids)
        )

    async def test_get_bank_updates_for_store_with_payment_account_and_time_range_invalid_payment_account_id(
        self,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        edit_histories = await payment_account_edit_history_repo.get_bank_updates_for_store_with_payment_account_and_time_range(
            payment_account_id=-1,
            start_time=datetime(2019, 9, 1),
            end_time=datetime.utcnow(),
        )
        assert len(edit_histories) == 0

    async def test_get_bank_updates_for_store_with_payment_account_and_time_range_success(
        self,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        start_time = datetime.utcnow() - timedelta(days=1)
        end_time = datetime.utcnow() + timedelta(days=1)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )

        original_edit_histories = await payment_account_edit_history_repo.get_bank_updates_for_store_with_payment_account_and_time_range(
            payment_account_id=payment_account.id,
            start_time=start_time,
            end_time=end_time,
        )

        payment_account_edit_history = await prepare_and_insert_payment_account_edit_history(
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            payment_account_id=payment_account.id,
            owner_type=BankUpdateHistoryOwnerType.STORE,
        )

        new_edit_histories = await payment_account_edit_history_repo.get_bank_updates_for_store_with_payment_account_and_time_range(
            payment_account_id=payment_account.id,
            start_time=start_time,
            end_time=end_time,
        )
        assert len(new_edit_histories) - len(original_edit_histories) == 1
        assert payment_account_edit_history in new_edit_histories
        assert payment_account_edit_history not in original_edit_histories
