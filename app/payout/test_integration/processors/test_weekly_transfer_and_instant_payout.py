import asyncio
from datetime import datetime
from app.commons.cache.cache import setup_cache

from app.payout.core.transfer.processors.create_transfer import (
    CreateTransfer,
    CreateTransferRequest,
)
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepository,
)
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepository,
)

from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_payout_card,
)
from app.payout.models import TransferType


import pytest
import pytest_mock
from asynctest import Mock

from app.commons.context.app_context import AppContext
from app.commons.operational_flags import ENABLED_PAYMENT_DB_LOCK_FOR_PAYOUT
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.conftest import RuntimeSetter
from app.payout.core.instant_payout.models import CreateAndSubmitInstantPayoutRequest
from app.payout.core.instant_payout.processor import InstantPayoutProcessors
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.repository.bankdb.payout_card import PayoutCardRepository
from app.payout.repository.bankdb.payout_method import PayoutMethodRepository
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepository,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepositoryInterface,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.paymentdb.payout_lock import PayoutLockRepository
from app.payout.test_integration.utils import prepare_and_insert_transaction


class TestWeeklyTransferAndInstantPayout:

    pytestmark = [pytest.mark.asyncio, pytest.mark.external]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
        payout_lock_repo: PayoutLockRepository,
        payout_repo: PayoutRepository,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        stripe_transfer_repo: StripeTransferRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        transfer_repo: TransferRepository,
        transaction_repo: TransactionRepository,
        app_context: AppContext,
        stripe_async_client: StripeAsyncClient,
    ):
        self.cache = setup_cache(app_context=app_context)
        self.dsj_client = app_context.dsj_client
        self.mocker = mocker
        self.managed_account_transfer_repo = managed_account_transfer_repo
        self.payment_account_repo = payment_account_repo
        self.payment_account_edit_history_repo = payment_account_edit_history_repo
        self.payout_lock_repo = payout_lock_repo
        self.payout_repo = payout_repo
        self.payout_card_repo = payout_card_repo
        self.payout_method_repo = payout_method_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.stripe_managed_account_transfer_repo = stripe_managed_account_transfer_repo
        self.stripe_payout_request_repo = stripe_payout_request_repo
        self.transfer_repo = transfer_repo
        self.transaction_repo = transaction_repo
        self.app_context = app_context
        self.stripe_async_client = stripe_async_client

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
            payment_lock_manager=self.app_context.redis_lock_manager,
            logger=self.mocker.Mock(),
            stripe=self.stripe_async_client,
            kafka_producer=self.app_context.kafka_producer,
            cache=self.cache,
            dsj_client=self.dsj_client,
            payout_lock_repo=self.payout_lock_repo,
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

    async def test_concurrent_process_weekly_transfer_and_instant_payout(
        self, runtime_setter: RuntimeSetter, mock_set_db_lock
    ):
        # prepare test data
        payment_account = await prepare_and_insert_payment_account(
            self.payment_account_repo
        )
        payout_card = await prepare_and_insert_payout_card(
            self.payout_method_repo,
            self.payout_card_repo,
            payout_account_id=payment_account.id,
            is_default=False,
        )

        payment_account_id = payment_account.id
        stripe_card_id = payout_card.stripe_card_id
        amount_to_submit = 1000

        await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo, payout_account_id=payment_account_id
        )

        # mock feature_flag
        data = {"enable_all": False, "white_list": [payment_account_id], "bucket": 0}
        runtime_setter.set(ENABLED_PAYMENT_DB_LOCK_FOR_PAYOUT, data)

        mock_create_with_redis_lock = self.mocker.patch(
            "app.payout.core.transfer.processors.create_transfer.CreateTransfer.create_with_redis_lock"
        )
        mock_create_payout_and_attach_to_txns = self.mocker.patch(
            "app.payout.repository.bankdb.payout.PayoutRepository.create_payout_and_attach_to_transactions"
        )

        # weekly transfer
        created_by_id = 9999
        create_transfer_op = self._construct_create_transfer_op(
            payment_account_id=payment_account_id,
            transfer_type=TransferType.MANUAL,
            created_by_id=created_by_id,
        )

        # instant payout
        create_and_submit_instant_payout_request = CreateAndSubmitInstantPayoutRequest(
            payout_account_id=payment_account_id,
            amount=amount_to_submit,
            currency="usd",
            card=stripe_card_id,
        )
        instant_payout_processor = InstantPayoutProcessors(
            logger=Mock(),
            payout_account_repo=self.payment_account_repo,
            payout_card_repo=self.payout_card_repo,
            payout_method_repo=self.payout_method_repo,
            payout_repo=self.payout_repo,
            stripe_managed_account_transfer_repo=self.stripe_managed_account_transfer_repo,
            stripe_payout_request_repo=self.stripe_payout_request_repo,
            transaction_repo=self.transaction_repo,
            stripe=self.stripe_async_client,
            payment_lock_manager=self.app_context.redis_lock_manager,
            payout_lock_repo=self.payout_lock_repo,
        )

        async def create_transfer():
            return await create_transfer_op._execute()

        async def create_instant_payout():
            return await instant_payout_processor.create_and_submit_instant_payout(
                create_and_submit_instant_payout_request
            )

        create_transfer_response, create_and_submit_intant_payout_response = await asyncio.gather(
            create_transfer(), create_instant_payout(), return_exceptions=True
        )
        mock_set_db_lock.assert_called_once()
        if create_transfer_response:
            mock_create_with_redis_lock.assert_called_once()
            mock_create_payout_and_attach_to_txns.assert_not_called()
        else:
            mock_create_with_redis_lock.assert_not_called()
            mock_create_payout_and_attach_to_txns.assert_called_once()
