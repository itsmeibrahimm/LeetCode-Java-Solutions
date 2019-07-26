from asyncio import gather
from dataclasses import dataclass
from fastapi import FastAPI
from gino import Gino
from structlog import BoundLogger
from typing import Any, cast

from app.commons.config.app_config import AppConfig
from app.commons.context.logger import root_logger


@dataclass(frozen=True)
class AppContext:
    log: BoundLogger
    payout_maindb_master: Gino
    payout_bankdb_master: Gino
    payin_maindb_master: Gino

    async def close(self):
        await gather(
            self.payout_maindb_master.pop_bind().close(),
            self.payout_bankdb_master.pop_bind().close(),
            self.payin_maindb_master.pop_bind().close(),
        )


async def create_app_context(config: AppConfig) -> AppContext:
    try:
        payout_maindb_master = await Gino(config.PAYOUT_MAINDB_URL.value)
    except Exception:
        root_logger.exception("failed to connect to payout main db")

    try:
        payout_bankdb_master = await Gino(config.PAYOUT_BANKDB_URL.value)
    except Exception:
        root_logger.exception("failed to connect to payout bank db")

    try:
        payin_maindb_master = await Gino(config.PAYIN_MAINDB_URL.value)
    except Exception:
        root_logger.exception("failed to connect to payin main db")

    context = AppContext(
        log=root_logger,
        payout_maindb_master=payout_maindb_master,
        payout_bankdb_master=payout_bankdb_master,
        payin_maindb_master=payin_maindb_master,
    )

    context.log.debug("app context created")

    return context


def set_context_for_app(app: FastAPI, context: AppContext):
    assert "context" not in app.extra, "app context is already set"
    app.extra["context"] = cast(Any, context)


def get_context_from_app(app: FastAPI) -> AppContext:
    context = app.extra.get("context")
    assert context is not None, "app context is set"
    assert isinstance(context, AppContext), "app context has correct type"
    return cast(AppContext, context)
