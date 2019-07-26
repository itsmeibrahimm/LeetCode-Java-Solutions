from asyncio import gather
from dataclasses import dataclass
from fastapi import FastAPI
from gino import Gino
from structlog import BoundLogger
from typing import Any, cast

from app.commons.config.app_config import AppConfig
from app.commons.context.logger import root_logger


@dataclass
class AppContext:
    _initialized = False
    log: BoundLogger
    payout_maindb_master: Gino
    payout_bankdb_master: Gino
    payin_maindb_master: Gino

    async def init(self, config: AppConfig):
        assert not self._initialized, "already initialized"

        self._initialized = True

        await gather(
            self.payout_maindb_master.set_bind(config.PAYOUT_MAINDB_URL.value),
            self.payout_bankdb_master.set_bind(config.PAYOUT_BANKDB_URL.value),
            self.payin_maindb_master.set_bind(config.PAYIN_MAINDB_URL.value),
        )

    async def close(self):
        await gather(
            self.payout_maindb_master.pop_bind().close(),
            self.payout_bankdb_master.pop_bind().close(),
            self.payin_maindb_master.pop_bind().close(),
        )


async def set_context_for_app(app: FastAPI, config: AppConfig) -> AppContext:
    assert "context" not in app.extra, "app context is already set"
    context = AppContext(
        log=root_logger,
        payout_maindb_master=Gino(),
        payout_bankdb_master=Gino(),
        payin_maindb_master=Gino(),
    )
    context.log.debug("app context created")

    await context.init(config)

    app.extra["context"] = cast(Any, context)
    return context


def get_context_from_app(app: FastAPI) -> AppContext:
    context = app.extra.get("context")
    assert isinstance(context, AppContext), "app context has correct type"
    return cast(AppContext, context)
