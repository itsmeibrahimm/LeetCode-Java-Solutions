from asyncio import gather
from dataclasses import dataclass
from typing import Any, cast

from app.commons.applications import FastAPI

from structlog import BoundLogger

from app.commons.config.app_config import AppConfig
from app.commons.context.logger import root_logger
from app.commons.database.model import Database
from app.commons.providers.stripe_client import StripeClientPool
from app.commons.providers.stripe_models import StripeClientSettings
from app.commons.providers.dsj_client import DSJClient


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

    dsj_client: DSJClient

    async def close(self):
        try:
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
        finally:
            # shutdown the threadpool
            self.stripe.shutdown(wait=False)


async def create_app_context(config: AppConfig) -> AppContext:
    try:
        payout_maindb = await Database.create(
            name="payout_maindb",
            db_config=config.DEFAULT_DB_CONFIG,
            master_url=config.PAYOUT_MAINDB_MASTER_URL,
            replica_url=config.PAYIN_MAINDB_REPLICA_URL,
        )
    except Exception:
        root_logger.exception("failed to connect to payout main db")
        raise

    try:
        payout_bankdb = await Database.create(
            name="payout_bankdb",
            db_config=config.DEFAULT_DB_CONFIG,
            master_url=config.PAYOUT_BANKDB_MASTER_URL,
            replica_url=config.PAYOUT_BANKDB_REPLICA_URL,
        )
    except Exception:
        root_logger.exception("failed to connect to payout bank db")
        raise

    try:
        payin_maindb = await Database.create(
            name="payin_maindb",
            db_config=config.DEFAULT_DB_CONFIG,
            master_url=config.PAYIN_MAINDB_MASTER_URL,
            replica_url=config.PAYIN_MAINDB_REPLICA_URL,
        )
    except Exception:
        root_logger.exception("failed to connect to payin main db")
        raise

    try:
        payin_paymentdb = await Database.create(
            name="payin_paymentdb",
            db_config=config.DEFAULT_DB_CONFIG,
            master_url=config.PAYIN_PAYMENTDB_MASTER_URL,
            replica_url=config.PAYIN_PAYMENTDB_REPLICA_URL,
        )
    except Exception:
        root_logger.exception("failed to connect to payin payment db")
        raise

    try:
        ledger_maindb = await Database.create(
            name="ledger_maindb",
            db_config=config.DEFAULT_DB_CONFIG,
            master_url=config.LEDGER_MAINDB_MASTER_URL,
            replica_url=config.LEDGER_MAINDB_REPLICA_URL,
        )
    except Exception:
        root_logger.exception("failed to connect to ledger main db")
        raise

    try:
        ledger_paymentdb = await Database.create(
            name="ledger_paymentdb",
            db_config=config.DEFAULT_DB_CONFIG,
            master_url=config.LEDGER_PAYMENTDB_MASTER_URL,
            replica_url=config.LEDGER_PAYMENTDB_REPLICA_URL,
        )
    except Exception:
        root_logger.exception("failed to connect to ledger payment db")
        raise

    stripe = StripeClientPool(
        settings_list=[
            StripeClientSettings(
                api_key=config.STRIPE_US_SECRET_KEY.value, country="US"
            )
        ],
        max_workers=config.STRIPE_MAX_WORKERS,
    )

    dsj_client = DSJClient(
        {
            "base_url": config.DSJ_API_BASE_URL,
            "email": config.DSJ_API_USER_EMAIL.value,
            "password": config.DSJ_API_USER_PASSWORD.value,
            "jwt_token_ttl": config.DSJ_API_JWT_TOKEN_TTL,
        }
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
        dsj_client=dsj_client,
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
