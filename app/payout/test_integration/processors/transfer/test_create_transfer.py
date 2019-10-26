import asyncio
from datetime import datetime, timezone

import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.database.infra import DB
from app.payout.core.exceptions import (
    PayoutError,
    PayoutErrorCode,
    payout_error_message_maps,
)

from app.payout.core.transfer.processors.create_transfer import (
    CreateTransfer,
    CreateTransferRequest,
)
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepository,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.model.transfer import TransferStatus

from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_transaction,
    prepare_and_insert_stripe_managed_account,
)
from app.payout.models import PayoutTargetType, TransferType


class TestCreateTransfer:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        transaction_repo: TransactionRepository,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
    ):
        self.create_transfer_operation = CreateTransfer(
            transfer_repo=transfer_repo,
            stripe_transfer_repo=stripe_transfer_repo,
            payment_account_repo=payment_account_repo,
            transaction_repo=transaction_repo,
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            logger=mocker.Mock(),
            request=CreateTransferRequest(
                payout_account_id=123,
                transfer_type=TransferType.SCHEDULED,
                bank_info_recently_changed=False,
                end_time=datetime.now(timezone.utc),
            ),
        )
        self.transfer_repo = transfer_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.payment_account_repo = payment_account_repo
        self.transaction_repo = transaction_repo
        self.payment_account_edit_history_repo = payment_account_edit_history_repo
        self.mocker = mocker

    @pytest.fixture
    def stripe_transfer_repo(self, payout_maindb: DB) -> StripeTransferRepository:
        return StripeTransferRepository(database=payout_maindb)

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def transaction_repo(self, payout_bankdb: DB) -> TransactionRepository:
        return TransactionRepository(database=payout_bankdb)

    @pytest.fixture
    def payment_account_edit_history_repo(
        self, payout_bankdb: DB
    ) -> PaymentAccountEditHistoryRepository:
        return PaymentAccountEditHistoryRepository(database=payout_bankdb)

    def _construct_create_transfer_op(
        self,
        payment_account_id: int,
        transfer_type=TransferType.SCHEDULED,
        payout_countries=None,
        target_type=None,
    ):
        return CreateTransfer(
            transfer_repo=self.transfer_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
            payment_account_repo=self.payment_account_repo,
            transaction_repo=self.transaction_repo,
            payment_account_edit_history_repo=self.payment_account_edit_history_repo,
            logger=self.mocker.Mock(),
            request=CreateTransferRequest(
                payout_account_id=payment_account_id,
                transfer_type=transfer_type,
                bank_info_recently_changed=False,
                end_time=datetime.utcnow(),
                payout_countries=payout_countries,
                target_type=target_type,
            ),
        )

    async def test_execute_create_transfer_no_payment_account(self):
        create_transfer_op = self._construct_create_transfer_op(payment_account_id=-1)
        with pytest.raises(PayoutError) as e:
            await create_transfer_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_PAYMENT_ACCOUNT_ID
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_PAYMENT_ACCOUNT_ID.value
            ]
        )

    async def test_execute_create_transfer_manual_transfer_type_success(self):
        # there is no corresponding stripe_transfer inserted, so the final status of transfer should be NEW
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transaction = await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo, payout_account_id=payment_account.id
        )
        create_transfer_op = self._construct_create_transfer_op(
            payment_account_id=payment_account.id, transfer_type=TransferType.MANUAL
        )
        response = await create_transfer_op._execute()
        assert response.transfer
        assert response.transfer.status == TransferStatus.NEW
        assert response.transfer.payment_account_id == payment_account.id
        assert response.transfer.amount == response.transfer.subtotal
        assert response.transfer.amount == transaction.amount
        assert transaction.id == response.transaction_ids[0]
        retrieved_transaction = await self.transaction_repo.get_transaction_by_id(
            transaction_id=transaction.id
        )
        assert retrieved_transaction
        assert retrieved_transaction.transfer_id == response.transfer.id

    async def test_execute_create_transfer_scheduled_transfer_type_invalid_country(
        self
    ):
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo, country_shortname="ABC"
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=sma.id
        )
        create_transfer_op = self._construct_create_transfer_op(
            payment_account_id=payment_account.id, payout_countries=["US"]
        )
        response = await create_transfer_op._execute()
        assert not response.transfer
        assert len(response.transaction_ids) == 0

    async def test_execute_create_transfer_scheduled_transfer_type_mx_blocked_for_payout(
        self
    ):
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo, country_shortname="US"
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=sma.id
        )
        create_transfer_op = self._construct_create_transfer_op(
            payment_account_id=payment_account.id,
            payout_countries=["US"],
            target_type=PayoutTargetType.STORE,
        )
        # mocked get_bool for runtime FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_json for runtime FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_int for runtime FRAUD_MINIMUM_HOURS_BEFORE_MX_PAYOUT_AFTER_BANK_CHANGE
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)
        self.mocker.patch("app.commons.runtime.runtime.get_json", return_value=[])
        self.mocker.patch("app.commons.runtime.runtime.get_int", return_value=12)

        @asyncio.coroutine
        def mock_get_bank_update(*args, **kwargs):
            return {"id": 1}

        self.mocker.patch(
            "app.payout.repository.bankdb.payment_account_edit_history.PaymentAccountEditHistoryRepository.get_bank_updates_for_store_with_payment_account_and_time_range",
            side_effect=mock_get_bank_update,
        )

        response = await create_transfer_op._execute()
        assert not response.transfer
        assert len(response.transaction_ids) == 0

    async def test_execute_create_transfer_scheduled_transfer_type_success(self):
        # there is no corresponding stripe_transfer inserted, so the final status of transfer should be NEW
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo, country_shortname="US"
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=sma.id
        )
        transaction = await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo, payout_account_id=payment_account.id
        )
        create_transfer_op = self._construct_create_transfer_op(
            payment_account_id=payment_account.id, payout_countries=["US"]
        )

        # mocked get_bool for runtime FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_json for runtime DISABLE_DASHER_PAYMENT_ACCOUNT_LIST_NAME, DISABLE_MERCHANT_PAYMENT_ACCOUNT_LIST_NAME
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=False)
        self.mocker.patch("app.commons.runtime.runtime.get_json", return_value=[])

        response = await create_transfer_op._execute()
        assert response.transfer
        assert response.transfer.status == TransferStatus.NEW
        assert response.transfer.payment_account_id == payment_account.id
        assert response.transfer.amount == response.transfer.subtotal
        assert response.transfer.amount == transaction.amount
        assert transaction.id == response.transaction_ids[0]
        retrieved_transaction = await self.transaction_repo.get_transaction_by_id(
            transaction_id=transaction.id
        )
        assert retrieved_transaction
        assert retrieved_transaction.transfer_id == response.transfer.id

    async def test_create_transfer_for_transactions_negative_amount(self):
        transaction = await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo, amount=-10, payout_account_id=123
        )
        transfer, transaction_ids = await self.create_transfer_operation.create_transfer_for_transactions(
            payment_account_id=123, unpaid_transactions=[transaction], currency="USD"
        )
        assert not transfer
        assert len(transaction_ids) == 0

    async def test_create_transfer_for_transactions_success(self):
        # transfer method is "", transfer status should be NEW
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transaction = await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo, payout_account_id=payment_account.id
        )
        transfer, transaction_ids = await self.create_transfer_operation.create_transfer_for_transactions(
            payment_account_id=payment_account.id,
            unpaid_transactions=[transaction],
            currency="USD",
        )
        assert transfer
        assert len(transaction_ids) == 1
        retrieved_transaction = await self.transaction_repo.get_transaction_by_id(
            transaction_id=transaction_ids[0]
        )
        assert retrieved_transaction
        assert retrieved_transaction.transfer_id == transfer.id
        assert transfer.status == TransferStatus.NEW

    async def test_create_with_redis_lock_no_unpaid_transactions(self):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer, transaction_ids = await self.create_transfer_operation.create_with_redis_lock(
            payment_account_id=payment_account.id,
            end_time=datetime.now(timezone.utc),
            currency="USD",
            start_time=None,
        )
        assert not transfer
        assert len(transaction_ids) == 0

    async def test_create_with_redis_lock_success(self):
        # transfer method is "", transfer status should be NEW
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo, payout_account_id=payment_account.id
        )
        transfer, transaction_ids = await self.create_transfer_operation.create_with_redis_lock(
            payment_account_id=payment_account.id,
            end_time=datetime.now(timezone.utc),
            currency="USD",
            start_time=None,
        )
        assert transfer
        assert len(transaction_ids) == 1
        retrieved_transaction = await self.transaction_repo.get_transaction_by_id(
            transaction_id=transaction_ids[0]
        )
        assert retrieved_transaction
        assert retrieved_transaction.transfer_id == transfer.id
        assert transfer.status == TransferStatus.NEW

    async def test_should_block_mx_payout_disable_payout_delay_after_bank_change(self):
        # mocked get_bool for runtime FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=False)
        assert not await self.create_transfer_operation.should_block_mx_payout(
            payout_date_time=datetime.utcnow(),
            payment_account_id=123,
            target_type=None,
            target_id=None,
            target_biz_id=None,
        )

    async def test_should_block_mx_payout_none_store_target(self):
        # mocked get_bool for runtime FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)
        assert not await self.create_transfer_operation.should_block_mx_payout(
            payout_date_time=datetime.utcnow(),
            payment_account_id=123,
            target_type=PayoutTargetType.DASHER,
            target_id=None,
            target_biz_id=None,
        )

    async def test_should_block_mx_payout_target_biz_id_in_list(self):
        # mocked get_bool for runtime FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_json for runtime FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)
        self.mocker.patch(
            "app.commons.runtime.runtime.get_json", return_value={123: "yay"}
        )
        assert not await self.create_transfer_operation.should_block_mx_payout(
            payout_date_time=datetime.utcnow(),
            payment_account_id=123,
            target_type=PayoutTargetType.STORE,
            target_id=None,
            target_biz_id=123,
        )

    async def test_should_block_mx_payout_time_window_to_check_in_hours_is_zero(self):
        # mocked get_bool for runtime FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_json for runtime FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_int for runtime FRAUD_MINIMUM_HOURS_BEFORE_MX_PAYOUT_AFTER_BANK_CHANGE
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)
        self.mocker.patch("app.commons.runtime.runtime.get_json", return_value=[])
        self.mocker.patch("app.commons.runtime.runtime.get_int", return_value=0)
        assert not await self.create_transfer_operation.should_block_mx_payout(
            payout_date_time=datetime.utcnow(),
            payment_account_id=123,
            target_type=PayoutTargetType.STORE,
            target_id=None,
            target_biz_id=123,
        )

    async def test_should_block_mx_payout_no_recent_bank_update(self):
        # mocked get_bool for runtime FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_json for runtime FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_int for runtime FRAUD_MINIMUM_HOURS_BEFORE_MX_PAYOUT_AFTER_BANK_CHANGE
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)
        self.mocker.patch("app.commons.runtime.runtime.get_json", return_value=[])
        self.mocker.patch("app.commons.runtime.runtime.get_int", return_value=12)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        assert not await self.create_transfer_operation.should_block_mx_payout(
            payout_date_time=datetime.utcnow(),
            payment_account_id=payment_account.id,
            target_type=PayoutTargetType.STORE,
            target_id=None,
            target_biz_id=123,
        )

    async def test_should_block_mx_payout_has_recent_bank_update_return_true(self):
        # mocked get_bool for runtime FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_json for runtime FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_int for runtime FRAUD_MINIMUM_HOURS_BEFORE_MX_PAYOUT_AFTER_BANK_CHANGE
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)
        self.mocker.patch("app.commons.runtime.runtime.get_json", return_value=[])
        self.mocker.patch("app.commons.runtime.runtime.get_int", return_value=12)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )

        @asyncio.coroutine
        def mock_get_bank_update(*args, **kwargs):
            return {"id": 1}

        self.mocker.patch(
            "app.payout.repository.bankdb.payment_account_edit_history.PaymentAccountEditHistoryRepository.get_bank_updates_for_store_with_payment_account_and_time_range",
            side_effect=mock_get_bank_update,
        )
        assert await self.create_transfer_operation.should_block_mx_payout(
            payout_date_time=datetime.utcnow(),
            payment_account_id=payment_account.id,
            target_type=PayoutTargetType.STORE,
            target_id=None,
            target_biz_id=123,
        )
