import os

import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.status import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE

from app.commons.applications import FastAPI
from app.commons.config.utils import init_app_config
from app.commons.context.app_context import (
    app_context_exists,
    create_app_context,
    get_context_from_app,
    remove_context_for_app,
    set_context_for_app,
)
from app.commons.context.logger import root_logger
from app.commons.error.errors import (
    PaymentErrorResponseBody,
    PaymentException,
    register_payment_exception_handler,
)
from app.example_v1.app import example_v1
from app.ledger.ledger import create_ledger_app
from app.middleware.doordash_metrics import (
    DoorDashMetricsMiddleware,
    init_global_statsd,
)
from app.middleware.req_context import ReqContextMiddleware
from app.payin.payin import create_payin_app
from app.payout.payout import create_payout_app

if os.getenv("DEBUGGER", "disabled").lower() == "enabled":
    from development import debug

    debug.bootstrap_debugger()

config = init_app_config()
app = FastAPI(title="Payment Service", debug=config.DEBUG)

# middleware needs to be added in reverse order due to:
# https://github.com/encode/starlette/issues/479
app.add_middleware(DoorDashMetricsMiddleware, config=config)
app.add_middleware(ReqContextMiddleware)
if config.SENTRY_CONFIG:
    sentry_sdk.init(
        dsn=config.SENTRY_CONFIG.dsn.value,
        environment=config.SENTRY_CONFIG.environment,
        release=config.SENTRY_CONFIG.release,
    )
    app.add_middleware(SentryAsgiMiddleware)
register_payment_exception_handler(app)


@app.get(
    "/health",
    status_code=HTTP_200_OK,
    responses={HTTP_503_SERVICE_UNAVAILABLE: {"model": PaymentErrorResponseBody}},
)
async def get_health():
    if app_context_exists(app):
        return "OK"
    raise PaymentException(
        http_status_code=HTTP_503_SERVICE_UNAVAILABLE,
        error_code="payment_service_unavailable",
        error_message="payment-service is not available or in progress of bootstrapping",
        retryable=True,
    )


@app.get("/error")
async def make_error():
    raise Exception("testing deployed sentry integration")


@app.on_event("startup")
async def startup():
    try:
        context = await create_app_context(config)
        set_context_for_app(app, context)
    except Exception:
        root_logger.exception("failed to create application context")
        raise

    # set up the global statsd client
    init_global_statsd(
        config.STATSD_PREFIX,
        host=config.STATSD_SERVER,
        fixed_tags={"env": config.ENVIRONMENT},
    )

    payout_app = create_payout_app(context)
    app.mount(payout_app.openapi_prefix, payout_app)

    payin_app = create_payin_app(context)
    app.mount(payin_app.openapi_prefix, payin_app)

    ledger_app = create_ledger_app(context)
    app.mount(ledger_app.openapi_prefix, ledger_app)

    app.mount(example_v1.openapi_prefix, example_v1)

    root_logger.info("====== Finished running application startup hooks. ======")


@app.on_event("shutdown")
async def shutdown():
    context = get_context_from_app(app)
    await context.close()
    remove_context_for_app(app, context)
