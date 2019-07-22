from __future__ import annotations

import logging

from fastapi import FastAPI

from .commons.config.utils import init_app_config
from .payin import payin
from .payout import payout

logger = logging.getLogger(__name__)

app = FastAPI()

app_config = init_app_config()
app.debug = app_config.DEBUG

app.mount(payout.app.openapi_prefix, payout.app)
app.mount(payin.app.openapi_prefix, payin.app)


@app.get("/")
async def root():
    return {"app": "base"}


@app.get("/health")
async def get_health():
    return "OK"


@app.on_event("startup")
async def startup():
    await payout.on_startup(app_config)
    await payin.on_startup(app_config)
    logger.info("********** main application started **********")


@app.on_event("shutdown")
async def shutdown():
    await payout.on_shutdown()
    await payin.on_shutdown()
    logger.info("********** main application shutting down **********")
