import asyncio

import pytest_mock
import pytest
from datetime import datetime, timedelta, timezone
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import UnknownTopicOrPartitionError

from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext
from app.commons.database.infra import DB
from app.commons.kafka import KafkaWorker
from app.payout import tasks
from app.payout.core.transfer.processors.submit_transfer import (
    SubmitTransferResponse,
    SubmitTransferRequest,
)
from app.payout.core.transfer.tasks.weekly_create_transfer_task import (
    WeeklyCreateTransferTask,
)
from app.payout.models import PayoutDay, TransferMethodType
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_transaction,
)

pytestmark = pytest.mark.asyncio


class TestKafkaWorker:
    topic_name = f"test_topic_{datetime.timestamp(datetime.now())}"
    payout_topic_name = "payment_payout"
    stripe_topic_name = "payment_stripe"
    num_partitions = 5

    @pytest.fixture(autouse=True)
    def setup(self, app_config: AppConfig):
        self.kafka_url = app_config.KAFKA_URL
        admin_client = KafkaAdminClient(
            bootstrap_servers=self.kafka_url, client_id="test"
        )

        topic_list = [
            NewTopic(
                name=self.topic_name,
                num_partitions=self.num_partitions,
                replication_factor=1,
            )
        ]
        try:
            admin_client.delete_topics([self.payout_topic_name, self.stripe_topic_name])
        except UnknownTopicOrPartitionError:
            pass
        admin_client.create_topics(new_topics=topic_list, validate_only=False)
        admin_client.close()

    def teardown(self):
        admin_client = KafkaAdminClient(
            bootstrap_servers=self.kafka_url, client_id="test"
        )
        try:
            admin_client.delete_topics(
                [self.topic_name, self.payout_topic_name, self.stripe_topic_name]
            )
        except UnknownTopicOrPartitionError:
            pass
        admin_client.close()

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def transaction_repo(self, payout_bankdb: DB) -> TransactionRepository:
        return TransactionRepository(database=payout_bankdb)

    async def test_success(
        self, app_context: AppContext, mocker: pytest_mock.MockFixture
    ):
        @asyncio.coroutine
        def mock_processor(*args, **kwargs):
            return True

        mock_message_processor = mocker.patch(
            "app.payout.tasks.process_message", side_effect=mock_processor
        )

        msg_list = []
        try:
            for i in range(10):
                msg = f"message {i}: {datetime.timestamp(datetime.now())}"
                msg_list.append(msg)
                await app_context.kafka_producer.send_and_wait(
                    self.topic_name, msg.encode()
                )
        except Exception as e:
            print(e)

        worker = KafkaWorker(
            app_context=app_context,
            topic_name=self.topic_name,
            kafka_url=self.kafka_url,
            processor=mock_message_processor,
            num_consumers=1,
        )

        await worker.start()
        # Stopping workers with graceful timeout set to 3 seconds
        await worker.stop(graceful_timeout_seconds=3)

        assert mock_message_processor.call_count == len(msg_list)
        for msg in msg_list:
            mock_message_processor.assert_any_call(app_context, msg.encode())

    async def test_weekly_create_transfer_success(
        self,
        app_context: AppContext,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transaction_repo: TransactionRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        transaction = await prepare_and_insert_transaction(
            transaction_repo=transaction_repo, payout_account_id=payment_account.id
        )

        @asyncio.coroutine
        def mock_execute_submit_transfer(*args, **kwargs):
            return SubmitTransferResponse()

        mocker.patch(
            "app.payout.core.transfer.processors.submit_transfer.SubmitTransfer.execute",
            side_effect=mock_execute_submit_transfer,
        )
        mocked_init_submit_transfer = mocker.patch.object(
            SubmitTransferRequest, "__init__", return_value=None
        )
        mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)

        end_time = datetime.now(timezone.utc).isoformat()
        unpaid_txn_start_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
        weekly_create_transfer_task = WeeklyCreateTransferTask(
            payout_day=PayoutDay.MONDAY,
            payout_countries=[],
            end_time=end_time,
            unpaid_txn_start_time=unpaid_txn_start_time,
            whitelist_payment_account_ids=[payment_account.id],
            exclude_recently_updated_accounts=False,
        )

        msg = weekly_create_transfer_task.serialize()
        await app_context.kafka_producer.send_and_wait(
            weekly_create_transfer_task.topic_name, msg.encode()
        )

        payout_worker = KafkaWorker(
            app_context=app_context,
            topic_name=self.payout_topic_name,
            kafka_url=self.kafka_url,
            processor=tasks.process_message,
            num_consumers=1,
        )
        stripe_worker = KafkaWorker(
            app_context=app_context,
            topic_name=self.stripe_topic_name,
            kafka_url=self.kafka_url,
            processor=tasks.process_message,
            num_consumers=1,
        )
        await payout_worker.start()
        await stripe_worker.start()

        # Stopping workers with graceful timeout set to 3 seconds
        await payout_worker.stop(graceful_timeout_seconds=3)
        await stripe_worker.stop(graceful_timeout_seconds=3)

        retrieved_transaction = await transaction_repo.get_transaction_by_id(
            transaction_id=transaction.id
        )
        assert retrieved_transaction
        transfer_id = retrieved_transaction.transfer_id

        mocked_init_submit_transfer.assert_called_once_with(
            transfer_id=transfer_id,
            method=TransferMethodType.STRIPE,
            retry=False,
            submitted_by=None,
        )
