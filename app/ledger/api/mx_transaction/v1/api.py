from fastapi import APIRouter

from app.commons.context.req_context import get_context_from_req
from app.commons.context.app_context import get_context_from_app
from app.commons.error.errors import (
    create_payment_error_response_blob,
    PaymentErrorResponseBody,
)
from app.ledger.api.mx_transaction.v1.request import CreateMxTransactionRequest
from app.ledger.core.mx_transaction.model import MxTransaction
from app.ledger.core.mx_transaction.processor import create_mx_transaction_impl

from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_501_NOT_IMPLEMENTED,
)

from app.ledger.repository.mx_transaction_repository import MxTransactionRepository


def create_mx_transactions_router(
    mx_transaction_repository: MxTransactionRepository
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/mx_transactions", status_code=HTTP_201_CREATED)
    async def create_mx_transaction_api(
        mx_transaction_request: CreateMxTransactionRequest, request: Request
    ):
        """
            Create a mx_transaction on DoorDash payments platform

            - **payment_account_id**: DoorDash consumer_id, store_id, or business_id
            - **target_type**: type that specifies the type of mx_transaction
            - **amount**: mx_transaction amount
            - **currency**: mx_transaction currency
            - **idempotency_key**: mx_transaction idempotency_key.
            - **context**: a context of mx_transaction
            - **metadata**: a metadata of mx_transaction
        """
        req_context = get_context_from_req(request)
        app_context = get_context_from_app(request.app)
        req_context.log.debug(
            f"Creating mx_transaction for payment_account {mx_transaction_request.payment_account_id}"
        )

        try:
            mx_transaction: MxTransaction = await create_mx_transaction_impl(
                app_context,
                req_context,
                mx_transaction_repository,
                mx_transaction_request.payment_account_id,
                mx_transaction_request.target_type,
                mx_transaction_request.amount,
                mx_transaction_request.currency,
                mx_transaction_request.idempotency_key,
                mx_transaction_request.routing_key,
                mx_transaction_request.target_id,
                mx_transaction_request.context,
                mx_transaction_request.metadata,
            )
            req_context.log.info("create_mx_transaction() completed. ")
        except Exception as e:
            req_context.log.error(
                "[create_mx_transaction][{}][{}] exception.".format(
                    mx_transaction_request.payment_account_id
                ),
                e,
            )
            return create_payment_error_response_blob(
                HTTP_500_INTERNAL_SERVER_ERROR,
                PaymentErrorResponseBody(
                    error_code="TODO: specific payment error_code",
                    error_message="TODO: specific payment error_message",
                    retryable="TODO: specific payment error retryable",
                ),
            )

        req_context.log.info(
            f"Created mx_transaction {mx_transaction.id} of type {mx_transaction.target_type} for payment_account {mx_transaction.payment_account_id}"
        )
        return mx_transaction

    @router.get("/api/v1/mx_transactions/{mx_transaction_id}")
    async def get_mx_transaction(
        mx_transaction_id: str, request: Request
    ) -> JSONResponse:
        req_context = get_context_from_req(request)
        # app_context = get_context_from_app(request.app)
        req_context.log.info(
            "get_mx_transaction() mx_transaction_id=%s", mx_transaction_id
        )

        return create_payment_error_response_blob(
            HTTP_501_NOT_IMPLEMENTED,
            PaymentErrorResponseBody(
                error_code="not implemented",
                error_message="not implemented",
                retryable=False,
            ),
        )

    return router
