from fastapi import APIRouter, Depends
from structlog import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.error.errors import (
    create_payment_error_response_blob,
    PaymentErrorResponseBody,
)
from app.ledger.api.mx_transaction.v1.request import CreateMxTransactionRequest
from app.ledger.core.exceptions import MxTransactionCreationError
from app.ledger.core.mx_transaction.model import MxTransaction
from app.ledger.core.mx_transaction.processor import MxTransactionProcessor

from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_501_NOT_IMPLEMENTED,
)


def create_mx_transactions_router() -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/mx_transactions", status_code=HTTP_201_CREATED)
    async def create_mx_transaction(
        mx_transaction_request: CreateMxTransactionRequest,
        log: BoundLogger = Depends(get_logger_from_req),
        mx_transaction_processor: MxTransactionProcessor = Depends(
            MxTransactionProcessor
        ),
    ):
        """
            Create a mx_transaction on DoorDash payments platform

            - **payment_account_id**: str
            - **target_type**: MxTransactionType, type of mx_transaction
            - **amount**: int, mx_transaction amount
            - **currency**: CurrencyType, mx_transaction currency
            - **idempotency_key**: str, mx_transaction idempotency_key.
            - **routing_key**: datetime, created_at of txn in DSJ or POS confirmation time
            - **interval_type**: MxLedgerIntervalType, specify how long the mx_ledger will be opened
            - **target_id**: Optional[str], id corresponding to mx_transaction type, e.g. delivery_id
            - **context**: Optional[Json], a context of mx_transaction
            - **metadata**: Optional[Json], metadata of mx_transaction
            - **legacy_transaction_id**: Optional[str], points to the corresponding txn in DSJ, used for migration purpose
        """
        log.debug(
            f"Creating mx_transaction for payment_account {mx_transaction_request.payment_account_id}"
        )

        try:
            mx_transaction: MxTransaction = await mx_transaction_processor.create(
                payment_account_id=mx_transaction_request.payment_account_id,
                target_type=mx_transaction_request.target_type,
                amount=mx_transaction_request.amount,
                currency=mx_transaction_request.currency,
                idempotency_key=mx_transaction_request.idempotency_key,
                routing_key=mx_transaction_request.routing_key,
                interval_type=mx_transaction_request.interval_type,
                target_id=mx_transaction_request.target_id,
                context=mx_transaction_request.context,
                metadata=mx_transaction_request.metadata,
                legacy_transaction_id=mx_transaction_request.legacy_transaction_id,
            )
            log.info("create_mx_transaction() completed. ")
        except MxTransactionCreationError as e:
            log.error(
                f"[create_mx_transaction] [{mx_transaction_request.payment_account_id}] Exception caught when creating txn. {e}"
            )
            return create_payment_error_response_blob(
                HTTP_500_INTERNAL_SERVER_ERROR,
                PaymentErrorResponseBody(
                    error_code=e.error_code,
                    error_message=e.error_message,
                    retryable=e.retryable,
                ),
            )

        log.info(
            f"Created mx_transaction {mx_transaction.id} of type {mx_transaction.target_type} for payment_account {mx_transaction.payment_account_id}"
        )
        return mx_transaction

    @router.get("/api/v1/mx_transactions/{mx_transaction_id}")
    async def get_mx_transaction(
        mx_transaction_id: str,
        request: Request,
        log: BoundLogger = Depends(get_logger_from_req),
    ) -> JSONResponse:
        log.info("get_mx_transaction() mx_transaction_id=%s", mx_transaction_id)

        return create_payment_error_response_blob(
            HTTP_501_NOT_IMPLEMENTED,
            PaymentErrorResponseBody(
                error_code="not implemented",
                error_message="not implemented",
                retryable=False,
            ),
        )

    return router
