from __future__ import annotations

import logging

from fastapi import FastAPI
from gino import Gino
from tenacity import retry, stop_after_attempt, wait_exponential

from .api.accounts_router import create_accounts_router
from .config import PayoutAppConfig
from .domain.repository import PayoutRepositories

logger = logging.getLogger(__name__)

# Declare db connection engines
maindb_connection = Gino()
bankdb_connection = Gino()

# Init data repositories
payout_repositories = PayoutRepositories(
    maindb_connection=maindb_connection, bankdb_connection=maindb_connection
)

# Declare sub app
app = FastAPI(openapi_prefix="/payout", description="Payout service")

# Mount api
accounts_router = create_accounts_router(
    payout_accounts=payout_repositories.payout_accounts
)
app.include_router(router=accounts_router, prefix="/accounts")


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=5))
async def on_startup(config: PayoutAppConfig):
    await maindb_connection.set_bind(config.PAYOUT_MAINDB_URL)
    await bankdb_connection.set_bind(config.PAYOUT_BANKDB_URL)
    logger.info("********** payout application started **********")


async def on_shutdown():
    await maindb_connection.pop_bind().close()
    await bankdb_connection.pop_bind().close()
    logger.info("********** payout application shutting down **********")
