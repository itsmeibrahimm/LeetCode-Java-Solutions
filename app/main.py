import os

from fastapi import FastAPI

from app.commons.config.utils import init_app_config
from app.commons.context.app_context import set_context_for_app
from app.example_v1.app import example_v1
from app.middleware.doordash_metrics import DoorDashMetricsMiddleware
from app.middleware.req_context import ReqContextMiddleware
from app.payin import payin
from app.payout import payout

if os.getenv("DEBUGGER", "disabled").lower() == "enabled":
    from development import debug

    debug.bootstrap_debugger()

app = FastAPI()
config = init_app_config()
app.debug = config.DEBUG
context = set_context_for_app(app, config)


@app.on_event("startup")
async def startup():
    await payout.on_startup(config)
    await payin.on_startup(config)
    context.log.info("********** main application started **********")


@app.on_event("shutdown")
async def shutdown():
    await payout.on_shutdown()
    await payin.on_shutdown()
    context.log.info("********** main application shutting down **********")


# middleware needs to be added in reverse order due to:
# https://github.com/encode/starlette/issues/479
app.add_middleware(DoorDashMetricsMiddleware, **config.METRICS_CONFIG)
app.add_middleware(ReqContextMiddleware)


@app.get("/health")
async def get_health():
    return "OK"


app.mount(example_v1.openapi_prefix, example_v1)
app.mount(payout.app.openapi_prefix, payout.app)
app.mount(payin.app.openapi_prefix, payin.app)
