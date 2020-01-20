import asyncio
import uuid

import pytest
from asynctest import patch
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import UnknownTopicOrPartitionError
from privacy import action_pb2, common_pb2

from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context, ReqContext
from app.commons.core.errors import DBOperationError
from app.commons.kafka import KafkaWorker
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payer.types import DeletePayerRequestStatus
from app.payin.kafka import delete_payer_message_processor
from app.payin.models.paymentdb import delete_payer_requests
from app.payin.repository.payer_repo import PayerRepository


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
    def action_request(self):
        action_request = action_pb2.ActionRequest()
        action_request.request_id = str(uuid.uuid4())
        action_request.action_id = action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET
        action_request.profile_type = common_pb2.ProfileType.CONSUMER
        action_request.profile_id = 1
        action_request.user_id = 1
        return action_request

    @pytest.fixture
    def req_context(self, app_context: AppContext) -> ReqContext:
        return build_req_context(app_context)

    @pytest.fixture
    def payer_client(
        self, app_context: AppContext, req_context: ReqContext
    ) -> PayerClient:
        return PayerClient(
            app_ctxt=app_context,
            log=req_context.log,
            payer_repo=PayerRepository(app_context),
            stripe_async_client=req_context.stripe_async_client,
        )

    @patch(
        "app.payin.kafka.delete_payer_message_processor.enable_delete_payer_request_ingestion",
        return_value=True,
    )
    async def test_insert_delete_payer_request_success(
        self,
        mock_enable_delete_payer_request_ingestion,
        app_context: AppContext,
        app_config: AppConfig,
        action_request,
        payer_client: PayerClient,
    ):
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

        delete_payer_requests = await payer_client.get_delete_payer_requests_by_client_request_id(
            client_request_id=uuid.UUID(action_request.request_id)
        )

        assert len(delete_payer_requests) == 1
        assert delete_payer_requests[0].consumer_id == 1
        assert delete_payer_requests[0].status == DeletePayerRequestStatus.IN_PROGRESS
        assert delete_payer_requests[0].acknowledged is False

    @patch(
        "app.payin.kafka.delete_payer_message_processor.send_response",
        return_value=True,
    )
    @patch(
        "app.payin.kafka.delete_payer_message_processor.enable_delete_payer_request_ingestion",
        return_value=True,
    )
    @patch("app.payin.kafka.delete_payer_message_processor.build_req_context")
    async def test_acknowledge_already_succeeded_but_not_acknowledged_request(
        self,
        mock_req_context,
        mock_enable_delete_payer_request_ingestion,
        mock_send_response,
        app_context: AppContext,
        app_config: AppConfig,
        action_request,
        payer_client,
        req_context: ReqContext,
    ):
        mock_req_context.return_value = req_context
        delete_payer_request = await payer_client.insert_delete_payer_request(
            client_request_id=action_request.request_id, consumer_id=1
        )

        await payer_client.update_delete_payer_request(
            client_request_id=delete_payer_request.client_request_id,
            status=DeletePayerRequestStatus.SUCCEEDED,
            summary=delete_payer_request.summary,
            retry_count=delete_payer_request.retry_count,
            acknowledged=False,
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

        delete_payer_requests_list = await payer_client.get_delete_payer_requests_by_client_request_id(
            client_request_id=uuid.UUID(action_request.request_id)
        )

        assert len(delete_payer_requests_list) == 1
        assert delete_payer_requests_list[0].consumer_id == 1
        assert (
            delete_payer_requests_list[0].status == DeletePayerRequestStatus.SUCCEEDED
        )
        assert delete_payer_requests_list[0].acknowledged is True

        mock_send_response.assert_called_once_with(
            app_context=app_context,
            log=req_context.log,
            request_id=action_request.request_id,
            action_id=action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
            status=common_pb2.StatusCode.COMPLETE,
            response=delete_payer_requests_list[0].summary,
        )

        await payer_client.payer_repo.payment_database.master().execute(
            delete_payer_requests.table.delete()
        )

    @patch(
        "app.payin.kafka.delete_payer_message_processor.send_response",
        return_value=True,
    )
    @patch(
        "app.payin.kafka.delete_payer_message_processor.enable_delete_payer_request_ingestion",
        return_value=True,
    )
    @patch("app.payin.kafka.delete_payer_message_processor.build_req_context")
    async def test_acknowledge_already_succeeded_and_acknowledged_request(
        self,
        mock_req_context,
        mock_enable_delete_payer_request_ingestion,
        mock_send_response,
        app_context: AppContext,
        app_config: AppConfig,
        action_request,
        payer_client,
        req_context: ReqContext,
    ):
        mock_req_context.return_value = req_context
        delete_payer_request = await payer_client.insert_delete_payer_request(
            client_request_id=action_request.request_id, consumer_id=1
        )

        await payer_client.update_delete_payer_request(
            client_request_id=delete_payer_request.client_request_id,
            status=DeletePayerRequestStatus.SUCCEEDED,
            summary=delete_payer_request.summary,
            retry_count=delete_payer_request.retry_count,
            acknowledged=True,
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

        delete_payer_requests_list = await payer_client.get_delete_payer_requests_by_client_request_id(
            client_request_id=uuid.UUID(action_request.request_id)
        )

        assert len(delete_payer_requests_list) == 1
        assert delete_payer_requests_list[0].consumer_id == 1
        assert (
            delete_payer_requests_list[0].status == DeletePayerRequestStatus.SUCCEEDED
        )
        assert delete_payer_requests_list[0].acknowledged is True

        mock_send_response.assert_called_once_with(
            app_context=app_context,
            log=req_context.log,
            request_id=action_request.request_id,
            action_id=action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
            status=common_pb2.StatusCode.COMPLETE,
            response=delete_payer_requests_list[0].summary,
        )

        await payer_client.payer_repo.payment_database.master().execute(
            delete_payer_requests.table.delete()
        )

    @patch(
        "app.payin.repository.payer_repo.PayerRepository.insert_delete_payer_request",
        side_effect=DBOperationError(error_message=""),
    )
    @patch(
        "app.payin.kafka.delete_payer_message_processor.send_response",
        return_value=True,
    )
    @patch(
        "app.payin.kafka.delete_payer_message_processor.enable_delete_payer_request_ingestion",
        return_value=True,
    )
    @patch("app.payin.kafka.delete_payer_message_processor.build_req_context")
    async def test_insert_delete_payer_request_failure(
        self,
        mock_req_context,
        mock_enable_delete_payer_request_ingestion,
        mock_send_response,
        mock_insert_delete_payer_request,
        app_context: AppContext,
        app_config: AppConfig,
        action_request,
        req_context: ReqContext,
    ):
        mock_req_context.return_value = req_context
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
            app_context=app_context,
            log=req_context.log,
            request_id=action_request.request_id,
            action_id=action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
            status=common_pb2.StatusCode.ERROR,
            response="Database error occurred. Please retry again",
        )

    @patch(
        "app.payin.kafka.delete_payer_message_processor.send_response",
        return_value=True,
    )
    @patch(
        "app.payin.kafka.delete_payer_message_processor.enable_delete_payer_request_ingestion",
        return_value=True,
    )
    @patch("app.payin.kafka.delete_payer_message_processor.build_req_context")
    async def test_invalid_action(
        self,
        mock_req_context,
        mock_enable_delete_payer_request_ingestion,
        mock_send_response,
        app_context: AppContext,
        app_config: AppConfig,
        action_request,
        req_context: ReqContext,
    ):
        mock_req_context.return_value = req_context
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
            app_context=app_context,
            log=req_context.log,
            request_id=action_request.request_id,
            action_id=action_pb2.ActionId.CONSUMER_FORGET,
            status=common_pb2.StatusCode.ERROR,
            response="Invalid Action Id",
        )

    @patch(
        "app.payin.kafka.delete_payer_message_processor.send_response",
        return_value=True,
    )
    @patch(
        "app.payin.kafka.delete_payer_message_processor.enable_delete_payer_request_ingestion",
        return_value=True,
    )
    @patch("app.payin.kafka.delete_payer_message_processor.build_req_context")
    async def test_invalid_profile_type(
        self,
        mock_req_context,
        mock_enable_delete_payer_request_ingestion,
        mock_send_response,
        app_context: AppContext,
        app_config: AppConfig,
        action_request,
        req_context: ReqContext,
    ):
        mock_req_context.return_value = req_context
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
            app_context=app_context,
            log=req_context.log,
            request_id=action_request.request_id,
            action_id=action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
            status=common_pb2.StatusCode.ERROR,
            response="Profile type is not consumer",
        )

    @patch(
        "app.payin.kafka.delete_payer_message_processor.send_response",
        return_value=True,
    )
    @patch(
        "app.payin.kafka.delete_payer_message_processor.enable_delete_payer_request_ingestion",
        return_value=True,
    )
    @patch("app.payin.kafka.delete_payer_message_processor.build_req_context")
    async def test_request_id_format_invalid(
        self,
        mock_req_context,
        mock_enable_delete_payer_request_ingestion,
        mock_send_response,
        app_context: AppContext,
        app_config: AppConfig,
        action_request,
        req_context: ReqContext,
    ):
        mock_req_context.return_value = req_context
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
            app_context=app_context,
            log=req_context.log,
            request_id=action_request.request_id,
            action_id=action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
            status=common_pb2.StatusCode.ERROR,
            response="Request Id format invalid. It must be a UUID.",
        )

    @patch(
        "app.payin.kafka.delete_payer_message_processor.send_response",
        return_value=True,
    )
    @patch(
        "app.payin.kafka.delete_payer_message_processor.enable_delete_payer_request_ingestion",
        return_value=True,
    )
    @patch("app.payin.kafka.delete_payer_message_processor.build_req_context")
    async def test_invalid_profile_id(
        self,
        mock_req_context,
        mock_enable_delete_payer_request_ingestion,
        mock_send_response,
        app_context: AppContext,
        app_config: AppConfig,
        action_request,
        req_context: ReqContext,
    ):
        mock_req_context.return_value = req_context
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
            app_context=app_context,
            log=req_context.log,
            request_id=action_request.request_id,
            action_id=action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
            status=common_pb2.StatusCode.ERROR,
            response="Invalid consumer id",
        )
