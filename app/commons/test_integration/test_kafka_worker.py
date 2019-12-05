import asyncio

import pytest_mock
from aiokafka import AIOKafkaProducer
import pytest
from datetime import datetime
from kafka import KafkaAdminClient
from kafka.admin import NewTopic

from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext
from app.commons.kafka import KafkaWorker


class TestKafkaWorker:
    pytestmark = [pytest.mark.asyncio]
    topic_name = f"test_topic_{datetime.timestamp(datetime.now())}"
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
        admin_client.create_topics(new_topics=topic_list, validate_only=False)
        admin_client.close()

    def teardown(self):
        admin_client = KafkaAdminClient(
            bootstrap_servers=self.kafka_url, client_id="test"
        )
        admin_client.delete_topics([self.topic_name])
        admin_client.close()

    async def test_success(
        self, app_context: AppContext, mocker: pytest_mock.MockFixture
    ):
        @asyncio.coroutine
        def mock_processor(*args, **kwargs):
            return True

        mock_message_processor = mocker.patch(
            "app.payout.tasks.process_message", side_effect=mock_processor
        )

        producer = AIOKafkaProducer(
            loop=asyncio.get_event_loop(), bootstrap_servers=self.kafka_url
        )
        await producer.start()

        msg_list = []
        try:
            for i in range(10):
                msg = f"message {i}: {datetime.timestamp(datetime.now())}"
                msg_list.append(msg)
                await producer.send_and_wait(self.topic_name, msg.encode())
        finally:
            # Wait for all pending messages to be delivered or expire.
            await producer.stop()

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
