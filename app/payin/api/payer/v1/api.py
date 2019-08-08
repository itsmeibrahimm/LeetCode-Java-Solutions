from fastapi import APIRouter

from app.commons.context.app_context import get_context_from_app, AppContext
from app.commons.context.req_context import get_context_from_req, ReqContext
from app.commons.error.errors import (
    PaymentErrorResponseBody,
    create_payment_error_response_blob,
)
from app.payin.api.payer.v1.request import CreatePayerRequest, UpdatePayerRequest
from app.payin.core.exceptions import (
    PayerCreationError,
    PayinErrorCode,
    PayerUpdateError,
)
from app.payin.core.payer.model import Payer
from app.payin.core.payer.processor import (
    create_payer_impl,
    get_payer_impl,
    update_payer_impl,
)

from starlette.requests import Request

from starlette.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_200_OK,
)

from app.payin.repository.payer_repo import PayerRepository


def create_payer_router(payer_repository: PayerRepository):
    router = APIRouter()

    @router.post("/api/v1/payers", status_code=HTTP_201_CREATED)
    async def create_payer(request: Request, req_body: CreatePayerRequest):
        """
        Create a payer on DoorDash payments platform

        - **dd_payer_id**: DoorDash consumer_id, store_id, or business_id
        - **payer_type**: type that specifies the role of payer
        - **email**: payer email
        - **country**: payer country. It will be used by payment gateway provider.
        - **description**: a description of payer
        """
        app_ctxt: AppContext = get_context_from_app(request.app)
        req_ctxt: ReqContext = get_context_from_req(request)
        req_ctxt.log.info(
            "[create_payer] dd_payer_id:%s payer_type:%s",
            req_body.dd_payer_id,
            req_body.payer_type,
        )
        try:
            payer: Payer = await create_payer_impl(
                payer_repository=payer_repository,
                app_ctxt=app_ctxt,
                req_ctxt=req_ctxt,
                dd_payer_id=req_body.dd_payer_id,
                payer_type=req_body.payer_type,
                email=req_body.email,
                country=req_body.country,
                description=req_body.description,
            )
            req_ctxt.log.info("[create_payer] onboard_payer() completed.")
        except PayerCreationError as e:
            return create_payment_error_response_blob(
                HTTP_500_INTERNAL_SERVER_ERROR,
                PaymentErrorResponseBody(
                    error_code=e.error_code,
                    error_message=e.error_message,
                    retryable=e.retryable,
                ),
            )

        return payer

    @router.get("/api/v1/payers/{payer_id}", status_code=HTTP_200_OK)
    async def get_payer(request: Request, payer_id: str, payer_type: str = None):
        """
        Get payer.

        - **payer_id**: DoorDash payer_id or stripe_customer_id
        """
        app_ctxt: AppContext = get_context_from_app(request.app)
        req_ctxt: ReqContext = get_context_from_req(request)

        req_ctxt.log.info("[get_payer] payer_id=%s", payer_id)
        try:
            payer: Payer = await get_payer_impl(
                payer_repository=payer_repository,
                app_ctxt=app_ctxt,
                req_ctxt=req_ctxt,
                payer_id=payer_id,
                payer_type=payer_type,
            )
            req_ctxt.log.info("[get_payer] retrieve_payer completed")
        except PayerCreationError as e:
            return create_payment_error_response_blob(
                (
                    HTTP_404_NOT_FOUND
                    if e.error_code == PayinErrorCode.PAYER_READ_NOT_FOUND.value
                    else HTTP_500_INTERNAL_SERVER_ERROR
                ),
                PaymentErrorResponseBody(
                    error_code=e.error_code,
                    error_message=e.error_message,
                    retryable=e.retryable,
                ),
            )

        return payer

    @router.patch("/api/v1/payers/{payer_id}", status_code=HTTP_200_OK)
    async def update_payer(
        request: Request, payer_id: str, req_body: UpdatePayerRequest
    ):
        """
        Update payer's default payment method

        - **default_payment_method_id**: payer's payment method (source) on authorized Payment Provider
        """
        app_ctxt: AppContext = get_context_from_app(request.app)
        req_ctxt: ReqContext = get_context_from_req(request)

        req_ctxt.log.info("[update_payer] payer_id=%s", payer_id)
        try:
            payer: Payer = await update_payer_impl(
                payer_repository=payer_repository,
                app_ctxt=app_ctxt,
                req_ctxt=req_ctxt,
                payer_id=payer_id,
                default_payment_method_id=req_body.default_payment_method_id,
                default_source_id=req_body.default_source_id,
                default_card_id=req_body.default_card_id,
                payer_id_type=req_body.payer_id_type,
                payer_type=req_body.payer_type,
            )
        except PayerUpdateError as e:
            if e.error_code == PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value:
                status = HTTP_400_BAD_REQUEST
            else:
                status = HTTP_500_INTERNAL_SERVER_ERROR

            return create_payment_error_response_blob(
                status,
                PaymentErrorResponseBody(
                    error_code=e.error_code,
                    error_message=e.error_message,
                    retryable=e.retryable,
                ),
            )

        return payer

    return router
