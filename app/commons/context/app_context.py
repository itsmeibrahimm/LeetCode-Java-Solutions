from asyncio import gather
from dataclasses import dataclass
from typing import Any, cast

from fastapi import FastAPI
from structlog import BoundLogger

from app.commons.config.app_config import AppConfig
from app.commons.context.logger import root_logger
from app.commons.database.model import Database
from app.commons.providers.stripe_client import StripeClientPool
from app.commons.providers.stripe_models import StripeClientSettings


@dataclass(frozen=True)
class AppContext:
    log: BoundLogger

    payout_maindb: Database
    payout_bankdb: Database
    payin_maindb: Database
    payin_paymentdb: Database
    ledger_maindb: Database
    ledger_paymentdb: Database

    stripe: StripeClientPool

    async def close(self):
        try:
            # shutdown the threadpool
            self.stripe.shutdown(wait=False)
        finally:
            await gather(
                # Too many Databases here, we may need to create some "manager" to push them down
                # Also current model assume each Database instance holds unique connection pool
                # The way of closing will break if we have same connection pool assigned to different Database instance
                self.payout_maindb.close(),
                self.payout_bankdb.close(),
                self.payin_maindb.close(),
                self.payin_paymentdb.close(),
                self.ledger_maindb.close(),
                self.ledger_paymentdb.close(),
            )


async def create_app_context(config: AppConfig) -> AppContext:
    try:
        payout_maindb = await Database(_master_url=config.PAYOUT_MAINDB_URL).init()
    except Exception:
        root_logger.exception("failed to connect to payout main db")

    try:
        payout_bankdb = await Database(_master_url=config.PAYOUT_BANKDB_URL).init()
    except Exception:
        root_logger.exception("failed to connect to payout bank db")

    try:
        payin_maindb = await Database(_master_url=config.PAYIN_MAINDB_URL).init()
    except Exception:
        root_logger.exception("failed to connect to payin main db")

    try:
        payin_paymentdb = await Database(_master_url=config.PAYIN_MAINDB_URL).init()
    except Exception:
        root_logger.exception("failed to connect to payin payment db")

    try:
        ledger_maindb = await Database(_master_url=config.LEDGER_MAINDB_URL).init()
    except Exception:
        root_logger.exception("failed to connect to ledger main db")

    try:
        ledger_paymentdb = await Database(_master_url=config.LEDGER_MAINDB_URL).init()
    except Exception:
        root_logger.exception("failed to connect to ledger payment db")

    stripe = StripeClientPool(
        settings_list=[
            StripeClientSettings(
                api_key=config.STRIPE_US_SECRET_KEY.value, country="US"
            )
        ],
        max_workers=config.STRIPE_MAX_WORKERS,
    )

    context = AppContext(
        log=root_logger,
        payout_maindb=payout_maindb,
        payout_bankdb=payout_bankdb,
        payin_maindb=payin_maindb,
        payin_paymentdb=payin_paymentdb,
        ledger_maindb=ledger_maindb,
        ledger_paymentdb=ledger_paymentdb,
        stripe=stripe,
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
