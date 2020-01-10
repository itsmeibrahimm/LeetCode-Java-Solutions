import asyncio
from datetime import datetime, timezone

import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.cache.cache import setup_cache
from app.commons.context.app_context import AppContext
from aioredlock.redis import Redis

from app.commons.core.errors import PaymentLockAcquireError
from app.conftest import RuntimeSetter
from app.main import config
from aioredlock import LockError
from app.payout.constants import (
    FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE,
    FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE,
    WEEKLY_TRANSFER_PAYOUT_BUSINESS_IDS_MAPPING,
    DISABLE_DASHER_PAYMENT_ACCOUNT_LIST_NAME,
    DISABLE_MERCHANT_PAYMENT_ACCOUNT_LIST_NAME,
    FRAUD_MINIMUM_HOURS_BEFORE_MX_PAYOUT_AFTER_BANK_CHANGE,
)
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.core.exceptions import (
    PayoutError,
    PayoutErrorCode,
    payout_error_message_maps,
)

from app.payout.core.transfer.processors.create_transfer import (
    CreateTransfer,
    CreateTransferRequest,
)
from app.payout.core.transfer.processors.submit_transfer import (
    SubmitTransferResponse,
    SubmitTransferRequest,
)
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepository,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepository,
)
from app.payout.repository.maindb.model.transfer import TransferStatus

from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_transaction,
    prepare_and_insert_stripe_managed_account,
)
from app.payout.models import PayoutTargetType, TransferType, PayoutDay


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
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        app_context: AppContext,
        stripe_async_client: StripeAsyncClient,
    ):
        self.cache = setup_cache(app_context=app_context)
        self.dsj_client = app_context.dsj_client
        self.create_transfer_operation = CreateTransfer(
            transfer_repo=transfer_repo,
            stripe_transfer_repo=stripe_transfer_repo,
            payment_account_repo=payment_account_repo,
            transaction_repo=transaction_repo,
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_lock_manager=app_context.redis_lock_manager,
            logger=mocker.Mock(),
            stripe=stripe_async_client,
            kafka_producer=app_context.kafka_producer,
            cache=self.cache,
            dsj_client=self.dsj_client,
            request=CreateTransferRequest(
                payout_account_id=123,
                transfer_type=TransferType.SCHEDULED,
                end_time=datetime.now(timezone.utc),
            ),
        )
        self.transfer_repo = transfer_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.payment_account_repo = payment_account_repo
        self.transaction_repo = transaction_repo
        self.payment_account_edit_history_repo = payment_account_edit_history_repo
        self.managed_account_transfer_repo = managed_account_transfer_repo
        self.payment_lock_manager = app_context.redis_lock_manager
        self.mocker = mocker
        self.stripe = stripe_async_client
        self.kafka_producer = app_context.kafka_producer

    def _construct_create_transfer_op(
        self,
        payment_account_id: int,
        transfer_type=TransferType.SCHEDULED,
        payout_countries=None,
        target_type=None,
        created_by_id=None,
        submit_after_creation=False,
        payout_day=None,
    ):
        return CreateTransfer(
            transfer_repo=self.transfer_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
            payment_account_repo=self.payment_account_repo,
            transaction_repo=self.transaction_repo,
            payment_account_edit_history_repo=self.payment_account_edit_history_repo,
            managed_account_transfer_repo=self.managed_account_transfer_repo,
            payment_lock_manager=self.payment_lock_manager,
            logger=self.mocker.Mock(),
            stripe=self.stripe,
            kafka_producer=self.kafka_producer,
            cache=self.cache,
            dsj_client=self.dsj_client,
            request=CreateTransferRequest(
                payout_account_id=payment_account_id,
                transfer_type=transfer_type,
                end_time=datetime.utcnow(),
                payout_countries=payout_countries,
                target_type=target_type,
                created_by_id=created_by_id,
                submit_after_creation=submit_after_creation,
                payout_day=payout_day,
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
        created_by_id = 9999
        create_transfer_op = self._construct_create_transfer_op(
            payment_account_id=payment_account.id,
            transfer_type=TransferType.MANUAL,
            created_by_id=created_by_id,
        )
        response = await create_transfer_op._execute()
        assert response.transfer
        assert response.transfer.status == TransferStatus.NEW
        assert response.transfer.payment_account_id == payment_account.id
        assert response.transfer.amount == response.transfer.subtotal
        assert response.transfer.amount == transaction.amount
        assert response.transfer.created_by_id == created_by_id
        assert response.transfer.manual_transfer_reason == "payout unpaid transactions"

        assert transaction.id == response.transaction_ids[0]
        retrieved_transaction = await self.transaction_repo.get_transaction_by_id(
            transaction_id=transaction.id
        )
        assert retrieved_transaction
        assert retrieved_transaction.transfer_id == response.transfer.id

    async def test_execute_create_transfer_manual_transfer_no_transactions_found(self):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        create_transfer_op = self._construct_create_transfer_op(
            payment_account_id=payment_account.id,
            transfer_type=TransferType.MANUAL,
            created_by_id=6666,
        )
        response = await create_transfer_op._execute()
        assert not response.transfer
        assert len(response.transaction_ids) == 0
        assert response.error_code == PayoutErrorCode.NO_UNPAID_TRANSACTION_FOUND

    async def test_execute_create_transfer_scheduled_transfer_type_payment_account_entity_not_found(
        self
    ):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, entity=None
        )
        create_transfer_op = self._construct_create_transfer_op(
            payment_account_id=payment_account.id, payout_day=PayoutDay.MONDAY
        )
        response = await create_transfer_op._execute()
        assert not response.transfer
        assert len(response.transaction_ids) == 0
        assert response.error_code == PayoutErrorCode.PAYMENT_ACCOUNT_ENTITY_NOT_FOUND

    async def test_execute_create_transfer_scheduled_transfer_type_payout_day_not_match(
        self
    ):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        create_transfer_op = self._construct_create_transfer_op(
            payment_account_id=payment_account.id, payout_day=PayoutDay.TUESDAY
        )
        response = await create_transfer_op._execute()
        assert not response.transfer
        assert len(response.transaction_ids) == 0
        assert response.error_code == PayoutErrorCode.PAYOUT_DAY_NOT_MATCH

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
        assert response.error_code == PayoutErrorCode.PAYOUT_COUNTRY_NOT_MATCH

    async def test_execute_create_transfer_scheduled_transfer_type_mx_blocked_for_payout(
        self, runtime_setter: RuntimeSetter
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
        runtime_setter.set(FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE, True)
        runtime_setter.set(
            "payout/feature-flags/enable_dsj_api_integration_for_weekly_payout.bool",
            True,
        )
        runtime_setter.set(
            FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE, []
        )
        runtime_setter.set(FRAUD_MINIMUM_HOURS_BEFORE_MX_PAYOUT_AFTER_BANK_CHANGE, 12)

        @asyncio.coroutine
        def mock_get_bank_update(*args, **kwargs):
            return {"id": 1}

        self.mocker.patch(
            "app.payout.repository.bankdb.payment_account_edit_history.PaymentAccountEditHistoryRepository.get_bank_updates_for_store_with_payment_account_and_time_range",
            side_effect=mock_get_bank_update,
        )

        @asyncio.coroutine
        def mock_dsj_client(*args, **kwargs):
            return {
                "target_type": PayoutTargetType.STORE.value,
                "target_id": 12345,
                "statement_descriptor": "yay",
                "business_id": 1,
            }

        self.mocker.patch(
            "app.commons.providers.dsj_client.DSJClient.get",
            side_effect=mock_dsj_client,
        )

        response = await create_transfer_op._execute()
        assert not response.transfer
        assert len(response.transaction_ids) == 0
        assert response.error_code == PayoutErrorCode.PAYMENT_BLOCKED

    async def test_execute_create_transfer_scheduled_transfer_type_success(
        self, runtime_setter: RuntimeSetter
    ):
        # there is no corresponding stripe_transfer inserted, so the final status of transfer should be NEW
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo, country_shortname="US"
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo,
            account_id=sma.id,
            entity="merchant",
        )
        transaction = await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo, payout_account_id=payment_account.id
        )
        create_transfer_op = self._construct_create_transfer_op(
            payment_account_id=payment_account.id,
            payout_countries=["US"],
            payout_day=PayoutDay.THURSDAY,
        )

        @asyncio.coroutine
        def mock_get_payment_account_ids_with_biz_id(*args, **kwargs):
            return [payment_account.id]

        mock_get_payment_account_ids = self.mocker.patch(
            "app.payout.core.transfer.processors.create_transfer.CreateTransfer.get_payment_account_ids_with_biz_id",
            side_effect=mock_get_payment_account_ids_with_biz_id,
        )

        runtime_setter.set(
            WEEKLY_TRANSFER_PAYOUT_BUSINESS_IDS_MAPPING[PayoutDay.MONDAY], []
        )
        runtime_setter.set(
            WEEKLY_TRANSFER_PAYOUT_BUSINESS_IDS_MAPPING[PayoutDay.TUESDAY], []
        )
        runtime_setter.set(
            WEEKLY_TRANSFER_PAYOUT_BUSINESS_IDS_MAPPING[PayoutDay.WEDNESDAY], []
        )
        runtime_setter.set(
            WEEKLY_TRANSFER_PAYOUT_BUSINESS_IDS_MAPPING[PayoutDay.THURSDAY], [123]
        )
        runtime_setter.set(
            WEEKLY_TRANSFER_PAYOUT_BUSINESS_IDS_MAPPING[PayoutDay.FRIDAY], []
        )
        runtime_setter.set(FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE, False)
        runtime_setter.set(DISABLE_DASHER_PAYMENT_ACCOUNT_LIST_NAME, [])
        runtime_setter.set(DISABLE_MERCHANT_PAYMENT_ACCOUNT_LIST_NAME, [])

        await self.cache.invalidate(key="thursday_payout_payment_accounts")
        response = await create_transfer_op._execute()
        assert response.transfer
        assert response.transfer.status == TransferStatus.NEW
        assert response.transfer.payment_account_id == payment_account.id
        assert response.transfer.amount == response.transfer.subtotal
        assert response.transfer.amount == transaction.amount

        assert not response.transfer.created_by_id
        assert not response.transfer.manual_transfer_reason
        assert transaction.id == response.transaction_ids[0]
        retrieved_transaction = await self.transaction_repo.get_transaction_by_id(
            transaction_id=transaction.id
        )
        assert retrieved_transaction
        assert retrieved_transaction.transfer_id == response.transfer.id

        # make sure retrieve payment account ids from given biz id is called
        mock_get_payment_account_ids.assert_called_once_with(
            business_id=123, dsj_client=self.dsj_client
        )

    async def test_execute_create_transfer_scheduled_transfer_type_submit_after_creation_success(
        self
    ):
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
            payment_account_id=payment_account.id,
            payout_countries=["US"],
            submit_after_creation=True,
        )

        # mocked get_bool for runtime FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_json for runtime DISABLE_DASHER_PAYMENT_ACCOUNT_LIST_NAME, DISABLE_MERCHANT_PAYMENT_ACCOUNT_LIST_NAME
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=False)
        self.mocker.patch("app.commons.runtime.runtime.get_json", return_value=[])

        @asyncio.coroutine
        def mock_execute_submit_transfer(*args, **kwargs):
            return SubmitTransferResponse()

        self.mocker.patch(
            "app.payout.core.transfer.processors.submit_transfer.SubmitTransfer.execute",
            side_effect=mock_execute_submit_transfer,
        )
        mocked_init_submit_transfer = self.mocker.patch.object(
            SubmitTransferRequest, "__init__", return_value=None
        )

        response = await create_transfer_op._execute()
        assert response.transfer
        assert response.transfer.status == TransferStatus.NEW
        assert response.transfer.payment_account_id == payment_account.id
        assert response.transfer.amount == response.transfer.subtotal
        assert response.transfer.amount == transaction.amount

        assert not response.transfer.created_by_id
        assert not response.transfer.manual_transfer_reason
        assert transaction.id == response.transaction_ids[0]
        retrieved_transaction = await self.transaction_repo.get_transaction_by_id(
            transaction_id=transaction.id
        )
        assert retrieved_transaction
        assert retrieved_transaction.transfer_id == response.transfer.id

        mocked_init_submit_transfer.assert_called_once_with(
            method="stripe",
            retry=False,
            submitted_by=None,
            transfer_id=response.transfer.id,
        )

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
            payout_date_time=datetime.utcnow(), payment_account_id=123
        )

    async def test_should_block_mx_payout_none_store_target(self):
        # mocked get_bool for runtime FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)

        @asyncio.coroutine
        async def mock_dsj_client(*args, **kwargs):
            return None

        self.mocker.patch(
            "app.commons.providers.dsj_client.DSJClient.get",
            side_effect=mock_dsj_client,
        )
        assert not await self.create_transfer_operation.should_block_mx_payout(
            payout_date_time=datetime.utcnow(), payment_account_id=123
        )

    async def test_should_block_mx_payout_target_biz_id_in_list(
        self, runtime_setter: RuntimeSetter
    ):
        # mocked get_bool for runtime FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_json for runtime FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE
        runtime_setter.set(FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE, True)
        runtime_setter.set(
            FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE, {123: "yay"}
        )
        assert not await self.create_transfer_operation.should_block_mx_payout(
            payout_date_time=datetime.utcnow(), payment_account_id=123
        )

    async def test_should_block_mx_payout_time_window_to_check_in_hours_is_zero(self):
        # mocked get_bool for runtime FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_json for runtime FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE
        # mocked get_int for runtime FRAUD_MINIMUM_HOURS_BEFORE_MX_PAYOUT_AFTER_BANK_CHANGE
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)
        self.mocker.patch("app.commons.runtime.runtime.get_json", return_value=[])
        self.mocker.patch("app.commons.runtime.runtime.get_int", return_value=0)

        @asyncio.coroutine
        async def mock_dsj_client(*args, **kwargs):
            return None

        self.mocker.patch(
            "app.commons.providers.dsj_client.DSJClient.get",
            side_effect=mock_dsj_client,
        )
        assert not await self.create_transfer_operation.should_block_mx_payout(
            payout_date_time=datetime.utcnow(), payment_account_id=123
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

        @asyncio.coroutine
        async def mock_dsj_client(*args, **kwargs):
            return None

        self.mocker.patch(
            "app.commons.providers.dsj_client.DSJClient.get",
            side_effect=mock_dsj_client,
        )
        assert not await self.create_transfer_operation.should_block_mx_payout(
            payout_date_time=datetime.utcnow(), payment_account_id=payment_account.id
        )

    async def test_should_block_mx_payout_has_recent_bank_update_return_true(
        self, runtime_setter: RuntimeSetter
    ):
        runtime_setter.set(FRAUD_ENABLE_MX_PAYOUT_DELAY_AFTER_BANK_CHANGE, True)
        runtime_setter.set(
            "payout/feature-flags/enable_dsj_api_integration_for_weekly_payout.bool",
            True,
        )
        runtime_setter.set(
            FRAUD_BUSINESS_WHITELIST_FOR_PAYOUT_DELAY_AFTER_BANK_CHANGE, []
        )
        runtime_setter.set(FRAUD_MINIMUM_HOURS_BEFORE_MX_PAYOUT_AFTER_BANK_CHANGE, 12)

        @asyncio.coroutine
        def mock_get_bank_update(*args, **kwargs):
            return {"id": 1}

        self.mocker.patch(
            "app.payout.repository.bankdb.payment_account_edit_history.PaymentAccountEditHistoryRepository.get_bank_updates_for_store_with_payment_account_and_time_range",
            side_effect=mock_get_bank_update,
        )

        @asyncio.coroutine
        def mock_dsj_client(*args, **kwargs):
            return {
                "target_type": PayoutTargetType.STORE.value,
                "target_id": 12345,
                "statement_descriptor": "yay",
                "business_id": 1,
            }

        self.mocker.patch(
            "app.commons.providers.dsj_client.DSJClient.get",
            side_effect=mock_dsj_client,
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )

        assert await self.create_transfer_operation.should_block_mx_payout(
            payout_date_time=datetime.utcnow(), payment_account_id=payment_account.id
        )

    async def test_create_transfer_for_unpaid_transactions_not_acquire_lock(
        self, app_context: AppContext, mock_set_lock
    ):
        mock_create_with_redis_lock = self.mocker.patch(
            "app.payout.core.transfer.processors.create_transfer.CreateTransfer.create_with_redis_lock"
        )
        # overwrite redis instances to some unknown address
        app_context.redis_lock_manager.redis = Redis(
            [("unknown_address", 1111)], config.REDIS_LOCK_DEFAULT_TIMEOUT
        )
        # Should raise PaymentLockAcquireError when can't connect to redis
        mock_set_lock.side_effect = LockError
        create_transfer_op = CreateTransfer(
            transfer_repo=self.transfer_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
            payment_account_repo=self.payment_account_repo,
            transaction_repo=self.transaction_repo,
            payment_account_edit_history_repo=self.payment_account_edit_history_repo,
            managed_account_transfer_repo=self.managed_account_transfer_repo,
            payment_lock_manager=self.payment_lock_manager,
            logger=self.mocker.Mock(),
            stripe=self.stripe,
            kafka_producer=self.kafka_producer,
            cache=self.cache,
            dsj_client=self.dsj_client,
            request=CreateTransferRequest(
                payout_account_id=111,
                transfer_type=TransferType.SCHEDULED,
                end_time=datetime.utcnow(),
                payout_countries=None,
                target_type=None,
            ),
        )
        with pytest.raises(PaymentLockAcquireError):
            await create_transfer_op.create_transfer_for_unpaid_transactions(
                payment_account_id=123,
                end_time=datetime.utcnow(),
                currency="usd",
                start_time=None,
            )

        mock_create_with_redis_lock.assert_not_called()
