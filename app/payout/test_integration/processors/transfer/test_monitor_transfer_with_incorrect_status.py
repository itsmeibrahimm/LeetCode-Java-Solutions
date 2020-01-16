import asyncio
from datetime import datetime, timezone

import pytest
import pytest_mock

from app.commons.cache.cache import setup_cache
from app.commons.context.app_context import AppContext

from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.conftest import RuntimeSetter
from app.payout.constants import (
    ENABLE_QUEUEING_MECHANISM_FOR_MONITOR_TRANSFER_WITH_INCORRECT_STATUS,
)
from app.payout.core.transfer.processors.monitor_transfer_with_incorrect_status import (
    MonitorTransferWithIncorrectStatusRequest,
    MonitorTransferWithIncorrectStatus,
)

from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    mock_payout,
    prepare_and_insert_transfer,
    prepare_and_insert_stripe_transfer,
)


class TestMonitorTransferWithIncorrectStatus:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        app_context: AppContext,
        stripe_async_client: StripeAsyncClient,
        runtime_setter: RuntimeSetter,
    ):
        self.cache = setup_cache(app_context=app_context)
        self.transfer_repo = transfer_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.payment_account_repo = payment_account_repo
        self.mocker = mocker
        self.stripe = stripe_async_client
        self.kafka_producer = app_context.kafka_producer
        self.runtime_setter = runtime_setter

    async def test_execute_monitor_transfer_with_incorrect_status_queue_disabled_success(
        self
    ):
        self.runtime_setter.set(
            ENABLE_QUEUEING_MECHANISM_FOR_MONITOR_TRANSFER_WITH_INCORRECT_STATUS, False
        )
        mocked_payout = mock_payout(status="paid")

        @asyncio.coroutine
        def mock_retrieve_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_payout",
            side_effect=mock_retrieve_payout,
        )

        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            payment_account_id=payment_account.id,
            status="pending",
        )
        stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="pending",
            stripe_id=mocked_payout.id,
        )

        @asyncio.coroutine
        def mock_list_transfers(*args, **kwargs):
            return [transfer.id]

        self.mocker.patch(
            "app.payout.repository.maindb.transfer.TransferRepository.get_transfers_by_submitted_at_and_method",
            side_effect=mock_list_transfers,
        )
        monitor_transfer_with_incorrect_status_req = MonitorTransferWithIncorrectStatusRequest(
            start_time=datetime.now(timezone.utc)
        )
        monitor_transfer_with_incorrect_status_op = MonitorTransferWithIncorrectStatus(
            transfer_repo=self.transfer_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
            stripe=self.stripe,
            kafka_producer=self.kafka_producer,
            request=monitor_transfer_with_incorrect_status_req,
        )
        await monitor_transfer_with_incorrect_status_op._execute()

        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == "paid"

        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_stripe_transfer_by_id(
            stripe_transfer_id=stripe_transfer.id
        )
        assert retrieved_stripe_transfer
        assert retrieved_stripe_transfer.stripe_status == "paid"
