import os

from fastapi import FastAPI

from app.commons.config.utils import init_app_config
from app.commons.context.app_context import get_context_from_app, set_context_for_app
from app.example_v1.app import example_v1
from app.middleware.doordash_metrics import DoorDashMetricsMiddleware
from app.middleware.req_context import ReqContextMiddleware
from app.payin.payin import create_payin_app
from app.payout.payout import create_payout_app

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
    context = await set_context_for_app(app, config)

    payout_app = create_payout_app(context)
    app.mount(payout_app.openapi_prefix, payout_app)

    payin_app = create_payin_app(context)
    app.mount(payin_app.openapi_prefix, payin_app)

    app.mount(example_v1.openapi_prefix, example_v1)


@app.on_event("shutdown")
async def shutdown():
    context = get_context_from_app(app)
    await context.close()
