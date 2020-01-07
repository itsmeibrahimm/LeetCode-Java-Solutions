import json
import uuid
from datetime import timezone, datetime

import psycopg2
from privacy import action_pb2, common_pb2

from app.commons.context.app_context import AppContext
from app.payin.core.payer.types import DeletePayerRequestStatus
from app.payin.repository.payer_repo import (
    DeletePayerRequestDbEntity,
    PayerRepository,
    FindDeletePayerRequestByClientRequestIdInput,
)

privacy_actions_topic = "privacy_actions"


async def process_message(app_context: AppContext, message: str):

    log = app_context.log

    log.info("Processing message.", consumer_payments_forget_message=message)

    payer_repository = PayerRepository(app_context)

    try:
        action_request = action_pb2.ActionRequest.FromString(message)
    except TypeError as type_error:
        log.error("Unable to deserialize the message", exc_info=type_error)
        action_request = action_pb2.ActionRequest.FromString(message.encode())

    if action_request.action_id != action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET:
        await send_response(
            app_context,
            action_request.request_id,
            action_request.action_id,
            common_pb2.StatusCode.ERROR,
            "Invalid Action Id",
        )
        return

    if action_request.profile_type != common_pb2.ProfileType.CONSUMER:
        await send_response(
            app_context,
            action_request.request_id,
            action_request.action_id,
            common_pb2.StatusCode.ERROR,
            "Profile type is not consumer",
        )
        return

    if action_request.profile_id < 0:
        await send_response(
            app_context,
            action_request.request_id,
            action_request.action_id,
            common_pb2.StatusCode.ERROR,
            "Invalid consumer id",
        )
        return

    try:
        existing_requests = await payer_repository.find_delete_payer_requests_by_client_request_id(
            find_delete_payer_request_by_client_request_id_input=FindDeletePayerRequestByClientRequestIdInput(
                client_request_id=uuid.UUID(action_request.request_id)
            )
        )
    except ValueError as value_error:
        log.error("Request Id format invalid. It must be a UUID.", exc_info=value_error)

        await send_response(
            app_context,
            action_request.request_id,
            action_request.action_id,
            common_pb2.StatusCode.ERROR,
            "Request Id format invalid. It must be a UUID.",
        )
        return

    if not existing_requests:
        summary = {
            "doordash.stripe_cards.pii.obfuscate": "IN_PROGRESS",
            "doordash.stripe_charges.pii.obfuscate": "IN_PROGRESS",
            "doordash.cart_payments.pii.obfuscate": "IN_PROGRESS",
            "pgp.stripe.customer.delete": "IN_PROGRESS",
        }
        try:
            delete_payer_request = await payer_repository.insert_delete_payer_request(
                DeletePayerRequestDbEntity(
                    id=uuid.uuid4(),
                    client_request_id=uuid.UUID(action_request.request_id),
                    consumer_id=action_request.profile_id,
                    payer_id=None,
                    status=DeletePayerRequestStatus.IN_PROGRESS.value,
                    summary=json.dumps(summary),
                    retry_count=0,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    acknowledged=False,
                )
            )

            log.info(
                "Added new delete payer request for processing.",
                request=delete_payer_request,
            )
        except psycopg2.Error as db_error:
            log.error("Database error occurred.", exc_info=db_error)
            await send_response(
                app_context,
                action_request.request_id,
                action_request.action_id,
                common_pb2.StatusCode.ERROR,
                "Database error occurred. Please retry again",
            )
            return


async def send_response(
    app_context: AppContext,
    request_id: str,
    action_id: action_pb2.ActionId,
    status: common_pb2.StatusCode,
    response: str,
):
    action_response = action_pb2.ActionResponse()
    action_response.request_id = request_id
    action_response.action_id = action_id
    action_response.status = status
    action_response.response = response
    await app_context.kafka_producer.produce(
        privacy_actions_topic, action_response.SerializeToString()
    )
