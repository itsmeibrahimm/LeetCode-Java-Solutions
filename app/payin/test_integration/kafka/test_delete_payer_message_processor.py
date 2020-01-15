import asyncio
import uuid

import psycopg2
import pytest
import pytest_mock
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import UnknownTopicOrPartitionError
from privacy import action_pb2, common_pb2

from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext
from app.commons.kafka import KafkaWorker
from app.payin.kafka import delete_payer_message_processor
from app.payin.repository.payer_repo import (
    PayerRepository,
    GetDeletePayerRequestsByClientRequestIdInput,
)


class TestDeletePayerMessageProcessor:
    consumer_topic = "consumer_payments_forget"
    num_partitions = 1
    pytestmark = pytest.mark.asyncio

    @pytest.fixture(autouse=True)
    def setup(self, app_config: AppConfig):
        self.kafka_url = app_config.KAFKA_URL
        admin_client = KafkaAdminClient(
            bootstrap_servers=self.kafka_url, client_id="test"
        )

        topic_list = [
            NewTopic(
                name=self.consumer_topic,
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
        try:
            admin_client.delete_topics([self.consumer_topic])
        except UnknownTopicOrPartitionError:
            pass
        admin_client.close()

    @pytest.fixture
    def mock_send_response(self, mocker: pytest_mock.MockFixture):
        return mocker.patch(
            "app.payin.kafka.delete_payer_message_processor.send_response"
        )

    @pytest.fixture
    def action_request(self):
        action_request = action_pb2.ActionRequest()
        action_request.request_id = str(uuid.uuid4())
        action_request.action_id = action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET
        action_request.profile_type = common_pb2.ProfileType.CONSUMER
        action_request.profile_id = 1
        action_request.user_id = 1
        return action_request

    async def test_insert_delete_payer_request_success(
        self, app_context: AppContext, app_config: AppConfig, action_request
    ):
        payer_repo = PayerRepository(app_context)

        await app_context.kafka_producer.produce(
            self.consumer_topic, action_request.SerializeToString()
        )

        delete_payer_kafka_worker = KafkaWorker(
            app_context=app_context,
            app_config=app_config,
            topic_name=self.consumer_topic,
            processor=delete_payer_message_processor.process_message,
            num_consumers=1,
        )

        await delete_payer_kafka_worker.start()

        await asyncio.sleep(10)

        # Stopping workers with graceful timeout set to 3 seconds
        await delete_payer_kafka_worker.stop(graceful_timeout_seconds=3)

        delete_payer_request = await payer_repo.get_delete_payer_requests_by_client_request_id(
            get_delete_payer_requests_by_client_request_id_input=GetDeletePayerRequestsByClientRequestIdInput(
                client_request_id=uuid.UUID(action_request.request_id)
            )
        )

        assert len(delete_payer_request) == 1
        assert delete_payer_request[0].consumer_id == 1

    async def test_insert_delete_payer_request_failure(
        self,
        app_context: AppContext,
        app_config: AppConfig,
        action_request,
        mocker: pytest_mock.MockFixture,
        mock_send_response,
    ):
        mocker.patch(
            "app.payin.repository.payer_repo.PayerRepository.insert_delete_payer_request",
            side_effect=psycopg2.IntegrityError(),
        )

        await app_context.kafka_producer.produce(
            self.consumer_topic, action_request.SerializeToString()
        )

        delete_payer_kafka_worker = KafkaWorker(
            app_context=app_context,
            app_config=app_config,
            topic_name=self.consumer_topic,
            processor=delete_payer_message_processor.process_message,
            num_consumers=1,
        )

        await delete_payer_kafka_worker.start()
        await asyncio.sleep(10)
        # Stopping workers with graceful timeout set to 3 seconds
        await delete_payer_kafka_worker.stop(graceful_timeout_seconds=3)

        mock_send_response.assert_called_once_with(
            app_context,
            action_request.request_id,
            action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
            common_pb2.StatusCode.ERROR,
            "Database error occurred. Please retry again",
        )

    async def test_invalid_action(
        self,
        app_context: AppContext,
        app_config: AppConfig,
        mock_send_response,
        action_request,
    ):
        action_request.action_id = action_pb2.ActionId.CONSUMER_FORGET

        await app_context.kafka_producer.produce(
            self.consumer_topic, action_request.SerializeToString()
        )

        delete_payer_kafka_worker = KafkaWorker(
            app_context=app_context,
            app_config=app_config,
            topic_name=self.consumer_topic,
            processor=delete_payer_message_processor.process_message,
            num_consumers=1,
        )

        await delete_payer_kafka_worker.start()
        await asyncio.sleep(10)
        # Stopping workers with graceful timeout set to 3 seconds
        await delete_payer_kafka_worker.stop(graceful_timeout_seconds=3)

        mock_send_response.assert_called_once_with(
            app_context,
            action_request.request_id,
            action_pb2.ActionId.CONSUMER_FORGET,
            common_pb2.StatusCode.ERROR,
            "Invalid Action Id",
        )

    async def test_invalid_profile_type(
        self,
        app_context: AppContext,
        app_config: AppConfig,
        mock_send_response,
        action_request,
    ):
        action_request.profile_type = common_pb2.ProfileType.UNKNOWN

        await app_context.kafka_producer.produce(
            self.consumer_topic, action_request.SerializeToString()
        )

        delete_payer_kafka_worker = KafkaWorker(
            app_context=app_context,
            app_config=app_config,
            topic_name=self.consumer_topic,
            processor=delete_payer_message_processor.process_message,
            num_consumers=1,
        )

        await delete_payer_kafka_worker.start()
        await asyncio.sleep(10)
        # Stopping workers with graceful timeout set to 3 seconds
        await delete_payer_kafka_worker.stop(graceful_timeout_seconds=3)

        mock_send_response.assert_called_once_with(
            app_context,
            action_request.request_id,
            action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
            common_pb2.StatusCode.ERROR,
            "Profile type is not consumer",
        )

    async def test_request_id_format_invalid(
        self,
        app_context: AppContext,
        app_config: AppConfig,
        mock_send_response,
        action_request,
    ):
        action_request.request_id = "test"

        await app_context.kafka_producer.produce(
            self.consumer_topic, action_request.SerializeToString()
        )

        delete_payer_kafka_worker = KafkaWorker(
            app_context=app_context,
            app_config=app_config,
            topic_name=self.consumer_topic,
            processor=delete_payer_message_processor.process_message,
            num_consumers=1,
        )

        await delete_payer_kafka_worker.start()
        await asyncio.sleep(10)
        # Stopping workers with graceful timeout set to 3 seconds
        await delete_payer_kafka_worker.stop(graceful_timeout_seconds=3)

        mock_send_response.assert_called_once_with(
            app_context,
            action_request.request_id,
            action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
            common_pb2.StatusCode.ERROR,
            "Request Id format invalid. It must be a UUID.",
        )

    async def test_invalid_profile_id(
        self,
        app_context: AppContext,
        app_config: AppConfig,
        mock_send_response,
        action_request,
    ):
        action_request.profile_id = -1

        await app_context.kafka_producer.produce(
            self.consumer_topic, action_request.SerializeToString()
        )

        delete_payer_kafka_worker = KafkaWorker(
            app_context=app_context,
            app_config=app_config,
            topic_name=self.consumer_topic,
            processor=delete_payer_message_processor.process_message,
            num_consumers=1,
        )

        await delete_payer_kafka_worker.start()
        await asyncio.sleep(10)
        # Stopping workers with graceful timeout set to 3 seconds
        await delete_payer_kafka_worker.stop(graceful_timeout_seconds=3)

        mock_send_response.assert_called_once_with(
            app_context,
            action_request.request_id,
            action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
            common_pb2.StatusCode.ERROR,
            "Invalid consumer id",
        )
