from fastapi import APIRouter, Depends
from structlog import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.error.errors import PaymentException, PaymentError
from app.payin.api.payer.v1.request import CreatePayerRequest, UpdatePayerRequest
from app.payin.core.exceptions import PayinErrorCode
from app.payin.core.payer.model import Payer
from app.payin.core.payer.processor import PayerProcessor

from starlette.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_200_OK,
)


def create_payer_router():
    router = APIRouter()

    @router.post("/api/v1/payers", status_code=HTTP_201_CREATED)
    async def create_payer(
        req_body: CreatePayerRequest,
        log: BoundLogger = Depends(get_logger_from_req),
        payer_processor: PayerProcessor = Depends(PayerProcessor),
    ) -> Payer:
        """
        Create a payer on DoorDash payments platform

        - **dd_payer_id**: DoorDash consumer_id, store_id, or business_id
        - **payer_type**: type that specifies the role of payer
        - **email**: payer email
        - **country**: payer country. It will be used by payment gateway provider.
        - **description**: a description of payer
        """
        log.info(
            "[create_payer] dd_payer_id:%s payer_type:%s",
            req_body.dd_payer_id,
            req_body.payer_type,
        )
        try:
            payer: Payer = await payer_processor.create(
                dd_payer_id=req_body.dd_payer_id,
                payer_type=req_body.payer_type,
                email=req_body.email,
                country=req_body.country,
                description=req_body.description,
            )
            log.info("[create_payer] onboard_payer() completed.")
        except PaymentError as e:
            raise PaymentException(
                http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                error_code=e.error_code,
                error_message=e.error_message,
                retryable=e.retryable,
            )
        return payer

    @router.get("/api/v1/payers/{payer_id}", status_code=HTTP_200_OK)
    async def get_payer(
        payer_id: str,
        payer_id_type: str = None,
        payer_type: str = None,
        force_update: bool = False,
        log: BoundLogger = Depends(get_logger_from_req),
        payer_processor: PayerProcessor = Depends(PayerProcessor),
    ) -> Payer:
        """
        Get payer.

        - **payer_id**: DoorDash payer_id or stripe_customer_id
        - **payer_type**: [string] identify the type of payer. Valid values include "marketplace",
                          "drive", "merchant", "store", "business" (default is "marketplace")
        - **payer_id_type**: [string] identify the type of payer_id. Valid values include "dd_payer_id",
                            "stripe_customer_id", "stripe_customer_serial_id" (default is "dd_payer_id")
        - **force_update**: [boolean] specify if requires a force update from Payment Provider (default is "false")
        """
        log.info("[get_payer] payer_id=%s", payer_id)
        try:
            payer: Payer = await payer_processor.get(
                payer_id=payer_id,
                payer_id_type=payer_id_type,
                payer_type=payer_type,
                force_update=force_update,
            )
            log.info("[get_payer] retrieve_payer completed")
        except PaymentError as e:
            raise PaymentException(
                http_status_code=(
                    HTTP_404_NOT_FOUND
                    if e.error_code == PayinErrorCode.PAYER_READ_NOT_FOUND.value
                    else HTTP_500_INTERNAL_SERVER_ERROR
                ),
                error_code=e.error_code,
                error_message=e.error_message,
                retryable=e.retryable,
            )
        return payer

    @router.patch("/api/v1/payers/{payer_id}", status_code=HTTP_200_OK)
    async def update_payer(
        payer_id: str,
        req_body: UpdatePayerRequest,
        log: BoundLogger = Depends(get_logger_from_req),
        payer_processor: PayerProcessor = Depends(PayerProcessor),
    ):
        """
        Update payer's default payment method

        - **default_payment_method**: payer's payment method (source) on authorized Payment Provider
        - **default_payment_method.id**: [string] identity of the payment method.
        - **default_payment_method.payment_method_id_type**: [string] identify the type of payment_method_id.
            Valid values include "dd_payment_method_id", "stripe_payment_method_id", "stripe_card_serial_id"
            (default is "dd_payment_method_id")
        """

        log.info("[update_payer] payer_id=%s", payer_id)
        try:
            payer: Payer = await payer_processor.update(
                payer_id=payer_id,
                default_payment_method_id=req_body.default_payment_method.id,
                payment_method_id_type=req_body.default_payment_method.payment_method_id_type,
            )
        except PaymentError as e:
            if e.error_code == PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value:
                status = HTTP_400_BAD_REQUEST
            else:
                status = HTTP_500_INTERNAL_SERVER_ERROR
            raise PaymentException(
                http_status_code=status,
                error_code=e.error_code,
                error_message=e.error_message,
                retryable=e.retryable,
            )
        return payer

    return router
