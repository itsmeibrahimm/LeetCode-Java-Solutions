from typing import Any, Awaitable, Callable, cast

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from app.commons.context.app_context import AppContext, get_app_context
from app.commons.context.req_context import get_req_context
from app.commons.config.utils import init_app_config
from app.payin import payin
from app.payout import payout
from app.example_v1.app import example_v1
from app.middleware.doordash_metrics import DoorDashMetricsMiddleware

app_config = init_app_config()
app_context = get_app_context(app_config)

app = FastAPI()
app.debug = app_config.DEBUG
app.extra["context"] = cast(Any, app_context)

app.add_middleware(
    DoorDashMetricsMiddleware,
    service_name="payment-service",
    cluster="local|staging|prod",
)


@app.middleware("http")
async def load_req_context_middleware(
    req: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    app_context = cast(AppContext, req.app.extra["context"])
    req_context = get_req_context(app_context)

    state = cast(Any, req.state)
    state.context = req_context

    resp = await call_next(req)
    return resp


@app.get("/health")
async def get_health():
    return "OK"


@app.on_event("startup")
async def startup():
    await payout.on_startup(app_config)
    await payin.on_startup(app_config)
    app_context.log.info("********** main application started **********")


@app.on_event("shutdown")
async def shutdown():
    await payout.on_shutdown()
    await payin.on_shutdown()
    app_context.log.info("********** main application shutting down **********")


app.mount(example_v1.openapi_prefix, example_v1)
app.mount(payout.app.openapi_prefix, payout.app)
app.mount(payin.app.openapi_prefix, payin.app)
