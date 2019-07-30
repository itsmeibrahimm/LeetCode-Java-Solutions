import os

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.commons.config.utils import init_app_config
from app.commons.context.app_context import (
    create_app_context,
    get_context_from_app,
    set_context_for_app,
)
from app.commons.context.logger import root_logger
from app.commons.error.errors import PaymentException, PaymentErrorResponseBody
from app.example_v1.app import example_v1
from app.middleware.doordash_metrics import DoorDashMetricsMiddleware
from app.middleware.req_context import ReqContextMiddleware
from app.payin.payin import create_payin_app
from app.payout.payout import create_payout_app

import logging

logger = logging.getLogger(__name__)

if os.getenv("DEBUGGER", "disabled").lower() == "enabled":
    from development import debug

    debug.bootstrap_debugger()

config = init_app_config()

app = FastAPI()
app.debug = config.DEBUG


# middleware needs to be added in reverse order due to:
# https://github.com/encode/starlette/issues/479
app.add_middleware(DoorDashMetricsMiddleware, **config.METRICS_CONFIG)
app.add_middleware(ReqContextMiddleware)


@app.get("/health")
async def get_health():
    return "OK"


@app.on_event("startup")
async def startup():
    try:
        context = await create_app_context(config)
        set_context_for_app(app, context)
    except Exception:
        root_logger.exception("failed to create application context")
        raise

    payout_app = create_payout_app(context)
    app.mount(payout_app.openapi_prefix, payout_app)

    payin_app = create_payin_app(context)
    app.mount(payin_app.openapi_prefix, payin_app)

    app.mount(example_v1.openapi_prefix, example_v1)


@app.on_event("shutdown")
async def shutdown():
    context = get_context_from_app(app)
    await context.close()


@app.exception_handler(PaymentException)
async def payment_exception_handler(request: Request, exception: PaymentException):
    return JSONResponse(
        status_code=exception.http_status_code,
        content=jsonable_encoder(
            PaymentErrorResponseBody(
                error_code=exception.error_code,
                error_message=exception.error_message,
                retryable=exception.retryable,
            )
        ),
    )
