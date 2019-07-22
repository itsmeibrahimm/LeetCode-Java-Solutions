import logging

from fastapi import FastAPI
from gino import Gino
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import PayinAppConfig

logger = logging.getLogger(__name__)

app = FastAPI(openapi_prefix="/payin", description="Payin service")

maindb_connection = Gino()


@app.get("/charges")
async def get_charges():
    return {"app": "Pay-In: Charges, Refunds, etc"}


@app.get("/refunds")
async def get_refunds():
    return {"app": "Pay-In: Charges, Refunds, etc"}


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=5))
async def on_startup(config: PayinAppConfig):
    await maindb_connection.set_bind(config.PAYIN_MAINDB_URL)
    logger.info("********** payin application started **********")


async def on_shutdown():
    logger.info("********** payin application shutting down **********")
