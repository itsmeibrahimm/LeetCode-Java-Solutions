import asyncio
from datetime import datetime, timezone, timedelta

import pytest
import pytest_mock

from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext

from app.commons.database.infra import DB
from app.commons.providers.stripe.stripe_client import StripeClient, StripeAsyncClient
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import StripeClientSettings
from app.commons.utils.pool import ThreadPoolHelper
from app.payout.core.transfer.processors.submit_transfer import (
    SubmitTransferResponse,
    SubmitTransferRequest,
)
from app.payout.core.transfer.processors.weekly_create_transfer import (
    WeeklyCreateTransfer,
    WeeklyCreateTransferRequest,
)
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepository,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepository,
)

from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_transaction,
    prepare_and_insert_stripe_managed_account,
    prepare_and_insert_payment_account_edit_history,
)
from app.payout.models import PayoutDay, PayoutTargetType


class TestWeeklyCreateTransfer:
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
        stripe: StripeAsyncClient,
    ):
        self.weekly_create_transfer_operation = WeeklyCreateTransfer(
            transfer_repo=transfer_repo,
            stripe_transfer_repo=stripe_transfer_repo,
            payment_account_repo=payment_account_repo,
            transaction_repo=transaction_repo,
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_lock_manager=app_context.redis_lock_manager,
            logger=mocker.Mock(),
            stripe=stripe,
            request=WeeklyCreateTransferRequest(
                payout_day=PayoutDay.MONDAY,
                payout_countries=[],
                unpaid_txn_start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                statement_descriptor="random descriptor",
                whitelist_payment_account_ids=[],
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
        self.stripe = stripe

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

    @pytest.fixture
    def managed_account_transfer_repo(
        self, payout_maindb: DB
    ) -> ManagedAccountTransferRepository:
        return ManagedAccountTransferRepository(database=payout_maindb)

    @pytest.fixture()
    def stripe(self, app_config: AppConfig):
        stripe_client = StripeClient(
            settings_list=[
                StripeClientSettings(
                    api_key=app_config.STRIPE_US_SECRET_KEY.value, country="US"
                )
            ],
            http_client=TimedRequestsClient(),
        )

        stripe_thread_pool = ThreadPoolHelper(
            max_workers=app_config.STRIPE_MAX_WORKERS, prefix="stripe"
        )

        stripe_async_client = StripeAsyncClient(
            executor_pool=stripe_thread_pool, stripe_client=stripe_client
        )
        yield stripe_async_client
        stripe_thread_pool.shutdown()

    def _construct_weekly_create_transfer_op(self, submit_after_creation=False):
        request = WeeklyCreateTransferRequest(
            payout_day=PayoutDay.MONDAY,
            payout_countries=[],
            end_time=datetime.utcnow(),
            unpaid_txn_start_time=datetime.utcnow() - timedelta(days=1),
            exclude_recently_updated_accounts=False,
            statement_descriptor="statement_descriptor",
            whitelist_payment_account_ids=[],
        )
        weekly_create_transfer_op = WeeklyCreateTransfer(
            payment_account_repo=self.payment_account_repo,
            payment_account_edit_history_repo=self.payment_account_edit_history_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_repo=self.transfer_repo,
            transaction_repo=self.transaction_repo,
            managed_account_transfer_repo=self.managed_account_transfer_repo,
            payment_lock_manager=self.payment_lock_manager,
            stripe=self.stripe,
            request=request,
        )
        return weekly_create_transfer_op

    async def test_get_payment_account_ids_blocked_by_ato_zero_block_hours(self):
        # mocked get_int for runtime variable DASHER_ATO_PREVENTION_THRESHOLD_IN_HOURS
        self.mocker.patch("app.commons.runtime.runtime.get_int", return_value=0)
        payment_account_ids = (
            await self.weekly_create_transfer_operation.get_payment_account_ids_blocked_by_ato()
        )
        assert len(payment_account_ids) == 0

    async def test_get_payment_account_ids_blocked_by_ato_success(self):
        # mocked get_int for runtime variable DASHER_ATO_PREVENTION_THRESHOLD_IN_HOURS
        self.mocker.patch("app.commons.runtime.runtime.get_int", return_value=24)
        original_payment_account_ids = (
            await self.weekly_create_transfer_operation.get_payment_account_ids_blocked_by_ato()
        )
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=sma.id
        )
        await prepare_and_insert_payment_account_edit_history(
            payment_account_edit_history_repo=self.payment_account_edit_history_repo,
            payment_account_id=payment_account.id,
            sma_id=sma.id,
        )
        new_payment_account_ids = (
            await self.weekly_create_transfer_operation.get_payment_account_ids_blocked_by_ato()
        )
        assert len(new_payment_account_ids) - len(original_payment_account_ids) == 1
        assert (
            list(set(new_payment_account_ids) - set(original_payment_account_ids))[0]
            == payment_account.id
        )

    async def test_execute_weekly_create_transfer_no_ato_check(self):
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=sma.id
        )
        transaction_a = await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo, payout_account_id=payment_account.id
        )
        transaction_b = await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo, payout_account_id=payment_account.id
        )

        @asyncio.coroutine
        def mock_get_payment_account_ids(*args, **kwargs):
            return [payment_account.id]

        self.mocker.patch(
            "app.payout.repository.bankdb.transaction.TransactionRepository.get_payout_account_ids_for_unpaid_transactions_without_limit",
            side_effect=mock_get_payment_account_ids,
        )

        @asyncio.coroutine
        def mock_check_payment_account_auto_paid(*args, **kwargs):
            return True

        self.mocker.patch(
            "app.payout.core.transfer.processors.create_transfer.CreateTransfer.should_payment_account_be_auto_paid_weekly",
            side_effect=mock_check_payment_account_auto_paid,
        )

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

        weekly_create_transfer_op = self._construct_weekly_create_transfer_op()
        await weekly_create_transfer_op._execute()
        retrieved_transaction_a = await self.transaction_repo.get_transaction_by_id(
            transaction_id=transaction_a.id
        )
        retrieved_transaction_b = await self.transaction_repo.get_transaction_by_id(
            transaction_id=transaction_b.id
        )
        assert retrieved_transaction_a
        assert retrieved_transaction_b
        transfer_id = retrieved_transaction_a.transfer_id
        assert transfer_id == retrieved_transaction_b.transfer_id

        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer_id
        )
        assert retrieved_transfer
        assert (
            retrieved_transfer.amount
            == retrieved_transaction_a.amount + retrieved_transaction_b.amount
        )

        # todo: update here once the target_id usage is settled
        mocked_init_submit_transfer.assert_called_once_with(
            method="stripe",
            retry=False,
            statement_descriptor="statement_descriptor",
            submitted_by=None,
            target_id=12345,
            target_type=PayoutTargetType.STORE,
            transfer_id=transfer_id,
        )
