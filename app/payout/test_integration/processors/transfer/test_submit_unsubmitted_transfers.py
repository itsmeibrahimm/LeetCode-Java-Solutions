import asyncio

import pytest
import pytest_mock

from app.commons.config.app_config import AppConfig
from app.commons.database.infra import DB
from app.commons.providers.stripe.stripe_client import StripeClient, StripeAsyncClient
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import StripeClientSettings
from app.commons.utils.pool import ThreadPoolHelper
from app.payout.core.transfer.processors.submit_transfer import (
    SubmitTransferResponse,
    SubmitTransferRequest,
)
from app.payout.core.transfer.processors.submit_unsubmitted_transfers import (
    SubmitUnsubmittedTransfers,
    SubmitUnsubmittedTransfersRequest,
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
from app.payout.test_integration.utils import prepare_and_insert_transfer


class TestSubmitUnsubmittedTransfer:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        transfer_repo: TransferRepository,
        transaction_repo: TransactionRepository,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
        stripe: StripeAsyncClient,
    ):
        self.submit_unsubmitted_transfers_operation = SubmitUnsubmittedTransfers(
            transfer_repo=transfer_repo,
            stripe_transfer_repo=stripe_transfer_repo,
            payment_account_repo=payment_account_repo,
            managed_account_transfer_repo=managed_account_transfer_repo,
            transaction_repo=transaction_repo,
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            logger=mocker.Mock(),
            stripe=stripe,
            request=SubmitUnsubmittedTransfersRequest(
                statement_descriptor="statement_descriptor"
            ),
        )
        self.transfer_repo = transfer_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.payment_account_repo = payment_account_repo
        self.managed_account_transfer_repo = managed_account_transfer_repo
        self.transaction_repo = transaction_repo
        self.payment_account_edit_history_repo = payment_account_edit_history_repo
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
    def managed_account_transfer_repo(
        self, payout_maindb: DB
    ) -> ManagedAccountTransferRepository:
        return ManagedAccountTransferRepository(database=payout_maindb)

    @pytest.fixture
    def transaction_repo(self, payout_bankdb: DB) -> TransactionRepository:
        return TransactionRepository(database=payout_bankdb)

    @pytest.fixture
    def payment_account_edit_history_repo(
        self, payout_bankdb: DB
    ) -> PaymentAccountEditHistoryRepository:
        return PaymentAccountEditHistoryRepository(database=payout_bankdb)

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

    async def test_execute_submit_unsubmitted_transfers(self):
        transfer_a = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.NEW
        )
        transfer_b = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.NEW
        )
        transfers = [transfer_a.id, transfer_b.id]

        @asyncio.coroutine
        def mock_get_unsubmitted_transfer_ids(*args, **kwargs):
            return transfers

        self.mocker.patch(
            "app.payout.repository.maindb.transfer.TransferRepository.get_unsubmitted_transfer_ids",
            side_effect=mock_get_unsubmitted_transfer_ids,
        )

        self.submit_unsubmitted_transfers_operation = SubmitUnsubmittedTransfers(
            transfer_repo=self.transfer_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
            payment_account_repo=self.payment_account_repo,
            managed_account_transfer_repo=self.managed_account_transfer_repo,
            transaction_repo=self.transaction_repo,
            payment_account_edit_history_repo=self.payment_account_edit_history_repo,
            logger=self.mocker.Mock(),
            stripe=self.stripe,
            request=SubmitUnsubmittedTransfersRequest(
                statement_descriptor="statement_descriptor"
            ),
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
        await self.submit_unsubmitted_transfers_operation._execute()
        mocked_init_submit_transfer.assert_any_call(
            method="stripe",
            retry=True,
            statement_descriptor="statement_descriptor",
            submitted_by=None,
            target_id=None,
            target_type=None,
            transfer_id=transfer_a.id,
        )
        mocked_init_submit_transfer.assert_any_call(
            method="stripe",
            retry=True,
            statement_descriptor="statement_descriptor",
            submitted_by=None,
            target_id=None,
            target_type=None,
            transfer_id=transfer_b.id,
        )
        assert mocked_init_submit_transfer.call_count == len(transfers)
