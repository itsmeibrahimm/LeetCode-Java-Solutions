from uuid import UUID

from confluent_kafka.cimpl import KafkaException
from privacy import action_pb2, common_pb2
from structlog import BoundLogger

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context
from app.payin.core.exceptions import PayerDeleteError
from app.payin.core.feature_flags import enable_delete_payer_request_ingestion
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payer.types import DeletePayerRequestStatus
from app.payin.repository.payer_repo import PayerRepository

privacy_actions_topic = "privacy_actions"


async def process_message(app_context: AppContext, message: str):
    """

    :param app_context:
    :param message:
    :return:
    Steps:
        1. Check if message is valid, if not send error response
        2. If there is any existing request for this message then check if it succeeded or failed previously
        without acknowledging. If so send appropriate acknowledgement and update existing request in db with
        new acknowledgement status
        3. If this message doesn't have an existing request than create a new request in db for later processing.
    """
    if not enable_delete_payer_request_ingestion():
        return

    req_context = build_req_context(app_context)

    payer_client = PayerClient(
        app_ctxt=app_context,
        log=req_context.log,
        payer_repo=PayerRepository(app_context),
        stripe_async_client=req_context.stripe_async_client,
    )

    log = req_context.log

    log.info(
        "[process_message] Processing message.",
        consumer_payments_forget_message=message,
    )

    try:
        action_request = action_pb2.ActionRequest.FromString(message)
    except TypeError:
        log.exception("[process_message] Unable to deserialize the message")
        action_request = action_pb2.ActionRequest.FromString(message.encode())

    if action_request.action_id != action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET:
        await send_response(
            app_context=app_context,
            log=log,
            request_id=action_request.request_id,
            action_id=action_request.action_id,
            status=common_pb2.StatusCode.ERROR,
            response="Invalid Action Id",
        )
        return

    if action_request.profile_type != common_pb2.ProfileType.CONSUMER:
        await send_response(
            app_context=app_context,
            log=log,
            request_id=action_request.request_id,
            action_id=action_request.action_id,
            status=common_pb2.StatusCode.ERROR,
            response="Profile type is not consumer",
        )
        return

    if action_request.profile_id < 0:
        await send_response(
            app_context=app_context,
            log=log,
            request_id=action_request.request_id,
            action_id=action_request.action_id,
            status=common_pb2.StatusCode.ERROR,
            response="Invalid consumer id",
        )
        return

    try:
        existing_requests = await payer_client.get_delete_payer_requests_by_client_request_id(
            UUID(action_request.request_id)
        )
    except ValueError:
        log.exception(
            "[process_message] Request Id format invalid. It must be a UUID.",
            consumer_id=action_request.profile_id,
            client_request_id=action_request.request_id,
        )

        await send_response(
            app_context=app_context,
            log=log,
            request_id=action_request.request_id,
            action_id=action_request.action_id,
            status=common_pb2.StatusCode.ERROR,
            response="Request Id format invalid. It must be a UUID.",
        )
        return

    if existing_requests:
        existing_delete_payer_request = existing_requests[0]
        acknowledged = existing_delete_payer_request.acknowledged

        if (
            not acknowledged
            and existing_delete_payer_request.status
            == DeletePayerRequestStatus.SUCCEEDED
        ):
            acknowledged = await send_response(
                app_context=app_context,
                log=log,
                request_id=str(existing_delete_payer_request.client_request_id),
                action_id=action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
                status=common_pb2.StatusCode.COMPLETE,
                response=existing_delete_payer_request.summary,
            )
        elif (
            not acknowledged
            and existing_delete_payer_request.status == DeletePayerRequestStatus.FAILED
        ):
            acknowledged = await send_response(
                app_context=app_context,
                log=log,
                request_id=str(existing_delete_payer_request.client_request_id),
                action_id=action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
                status=common_pb2.StatusCode.ERROR,
                response=existing_delete_payer_request.summary,
            )

        if acknowledged:
            try:
                await payer_client.update_delete_payer_request(
                    client_request_id=existing_delete_payer_request.client_request_id,
                    status=existing_delete_payer_request.status,
                    summary=existing_delete_payer_request.summary,
                    retry_count=existing_delete_payer_request.retry_count,
                    acknowledged=acknowledged,
                )
            except PayerDeleteError:
                log.exception(
                    "[process_message] Database exception occurred with updating delete payer request",
                    consumer_id=existing_delete_payer_request.consumer_id,
                    client_request_id=existing_delete_payer_request.client_request_id,
                )
    else:
        try:
            delete_payer_request = await payer_client.insert_delete_payer_request(
                client_request_id=UUID(action_request.request_id),
                consumer_id=action_request.profile_id,
            )

            log.info(
                "[process_message] Added new delete payer request for processing.",
                request=delete_payer_request,
            )
        except PayerDeleteError:
            log.exception(
                "[process_message] Database error occurred.",
                consumer_id=action_request.profile_id,
                client_request_id=action_request.request_id,
            )
            await send_response(
                app_context=app_context,
                log=log,
                request_id=action_request.request_id,
                action_id=action_request.action_id,
                status=common_pb2.StatusCode.ERROR,
                response="Database error occurred. Please retry again",
            )


async def send_response(
    app_context: AppContext,
    log: BoundLogger,
    request_id: str,
    action_id: action_pb2.ActionId,
    status: common_pb2.StatusCode,
    response: str,
) -> bool:
    action_response = action_pb2.ActionResponse()
    action_response.request_id = request_id
    action_response.action_id = action_id
    action_response.status = status
    action_response.response = response
    try:
        await app_context.kafka_producer.produce(
            privacy_actions_topic, action_response.SerializeToString()
        )
        log.info(
            "[send_response] Sent action response.",
            client_request_id=request_id,
            response_message=response,
        )
        return True
    except KafkaException:
        log.exception(
            "[send_response] Kafka exception occurred with sending action response",
            client_request_id=request_id,
            response_message=response,
        )
        return False
