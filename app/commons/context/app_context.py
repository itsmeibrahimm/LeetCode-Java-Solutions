import asyncio
from asyncio import gather
from dataclasses import dataclass
from random import choice
from typing import Any, cast

import aiohttp
from starlette.requests import Request
from structlog.stdlib import BoundLogger

from app.commons.applications import FastAPI
from app.commons.config.app_config import AppConfig
from app.commons.context.logger import root_logger, get_logger
from app.commons.database.infra import DB
from app.commons.providers.timed_aio_client import (
    TrackedIdentityClientSession,
    TrackedDsjClientSession,
)
from app.commons.providers.dsj_client import DSJClient
from app.commons.providers.identity_client import (
    IdentityClientInterface,
    IdentityClient,
    StubbedIdentityClient,
)
from app.commons.providers.stripe.stripe_client import StripeClient
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import StripeClientSettings
from app.commons.types import CountryCode
from app.commons.utils.pool import ThreadPoolHelper

from doordash_python_stats.ddstats import doorstats_global
from app.commons.instrumentation.monitor import MonitoringManager
from app.commons.instrumentation.eventloop import EventLoopMonitor
from app.commons.instrumentation.memtrace import MemTraceMonitor
from app.commons.instrumentation.pool import stat_thread_pool_jobs
from app.payin.capture.service import CaptureService


@dataclass(frozen=True)
class AppContext:
    log: BoundLogger

    monitor: MonitoringManager

    payout_maindb: DB
    payout_bankdb: DB
    payin_maindb: DB
    payin_paymentdb: DB
    ledger_maindb: DB
    ledger_paymentdb: DB

    stripe_thread_pool: ThreadPoolHelper

    stripe_client: StripeClient

    dsj_client: DSJClient

    identity_client: IdentityClientInterface

    capture_service: CaptureService

    ids_session: aiohttp.ClientSession

    dsj_session: aiohttp.ClientSession

    async def close(self):
        # stop monitoring various application resources
        self.monitor.stop()

        try:
            await gather(
                # Too many Databases here, we may need to create some "manager" to push them down
                # Also current model assume each Database instance holds unique connection pool
                # The way of closing will break if we have same connection pool assigned to different Database instance
                self.payout_maindb.disconnect(),
                self.payout_bankdb.disconnect(),
                self.payin_maindb.disconnect(),
                self.payin_paymentdb.disconnect(),
                self.ledger_maindb.disconnect(),
                self.ledger_paymentdb.disconnect(),
                self.ids_session.close(),
                self.dsj_session.close(),
            )
        finally:
            # shutdown the threadpool
            self.stripe_thread_pool.shutdown(wait=False)


async def create_app_context(config: AppConfig) -> AppContext:

    # periodic monitoring for application resources
    monitor_logger = get_logger("monitoring")
    monitor = MonitoringManager(
        logger=monitor_logger, stats_client=doorstats_global, default_interval_secs=30
    )

    # monitor: asyncio event loop task depth, latency
    monitor.add(
        EventLoopMonitor(interval_secs=config.MONITOR_INTERVAL_EVENT_LOOP_LATENCY),
        interval_secs=config.MONITOR_INTERVAL_EVENT_LOOP_LATENCY,
    )

    # monitor: mem trace for each pid
    monitor.add(
        MemTraceMonitor(interval_secs=config.MONITOR_INTERVAL_MEM_TRACE),
        interval_secs=config.MONITOR_INTERVAL_MEM_TRACE,
    )

    # Pick up a maindb replica upfront and use it for all instances targeting maindb
    # Not do randomization separately in each creation to reduce the chance that
    # app_context initialization fails due to any one of the replicas has outage
    selected_maindb_replica = (
        choice(config.AVAILABLE_MAINDB_REPLICAS)
        if config.AVAILABLE_MAINDB_REPLICAS
        else None
    )

    payout_maindb = DB.create_with_alternative_replica(
        db_id="payout_maindb",
        db_config=config.DEFAULT_DB_CONFIG,
        master_url=config.PAYOUT_MAINDB_MASTER_URL,
        replica_url=config.PAYOUT_MAINDB_REPLICA_URL,
        alternative_replica=selected_maindb_replica,
    )

    payin_maindb = DB.create_with_alternative_replica(
        db_id="payin_maindb",
        db_config=config.DEFAULT_DB_CONFIG,
        master_url=config.PAYIN_MAINDB_MASTER_URL,
        replica_url=config.PAYIN_MAINDB_REPLICA_URL,
        alternative_replica=selected_maindb_replica,
    )

    ledger_maindb = DB.create_with_alternative_replica(
        db_id="ledger_maindb",
        db_config=config.DEFAULT_DB_CONFIG,
        master_url=config.LEDGER_MAINDB_MASTER_URL,
        replica_url=config.LEDGER_MAINDB_REPLICA_URL,
        alternative_replica=selected_maindb_replica,
    )

    payout_bankdb = DB.create(
        db_id="payout_bankdb",
        db_config=config.DEFAULT_DB_CONFIG,
        master_url=config.PAYOUT_BANKDB_MASTER_URL,
        replica_url=config.PAYOUT_BANKDB_REPLICA_URL,
    )

    payin_paymentdb = DB.create(
        db_id="payin_paymentdb",
        db_config=config.DEFAULT_DB_CONFIG,
        master_url=config.PAYIN_PAYMENTDB_MASTER_URL,
        replica_url=config.PAYIN_PAYMENTDB_REPLICA_URL,
    )

    ledger_paymentdb = DB.create(
        db_id="ledger_paymentdb",
        db_config=config.DEFAULT_DB_CONFIG,
        master_url=config.LEDGER_PAYMENTDB_MASTER_URL,
        replica_url=config.LEDGER_PAYMENTDB_REPLICA_URL,
    )

    if "payout" in config.INCLUDED_APPS:
        await asyncio.gather(payout_maindb.connect(), payout_bankdb.connect())

    if "payin" in config.INCLUDED_APPS:
        await asyncio.gather(payin_maindb.connect(), payin_paymentdb.connect())

    if "ledger" in config.INCLUDED_APPS:
        await asyncio.gather(ledger_maindb.connect(), ledger_paymentdb.connect())

    stripe_client = StripeClient(
        settings_list=[
            # TODO: add CA/AU
            StripeClientSettings(
                api_key=config.STRIPE_US_SECRET_KEY.value, country=CountryCode.US
            ),
            StripeClientSettings(
                api_key=config.STRIPE_AU_SECRET_KEY.value, country=CountryCode.AU
            ),
            StripeClientSettings(
                api_key=config.STRIPE_CA_SECRET_KEY.value, country=CountryCode.CA
            ),
        ],
        http_client=TimedRequestsClient(),
    )

    stripe_thread_pool = ThreadPoolHelper(
        max_workers=config.STRIPE_MAX_WORKERS, prefix="stripe"
    )
    # monitor: stripe thread pool job pool
    monitor.add(
        stat_thread_pool_jobs(
            pool_name="stripe", pool_job_stats=stripe_thread_pool.executor
        ),
        interval_secs=config.MONITOR_INTERVAL_RESOURCE_JOB_POOL,
    )

    ids_session: aiohttp.ClientSession = TrackedIdentityClientSession()
    dsj_session: aiohttp.ClientSession = TrackedDsjClientSession()

    # This can probably be provided/constructed at the Request/Job/Func level eventually. The true resource here is
    # the dsj_session. Similarly identity_client could also be removed, although the stubbing makes it more complex
    dsj_client = DSJClient(
        session=dsj_session,
        client_config={
            "base_url": config.DSJ_API_BASE_URL,
            "email": config.DSJ_API_USER_EMAIL.value,
            "password": config.DSJ_API_USER_PASSWORD.value,
            "jwt_token_ttl": config.DSJ_API_JWT_TOKEN_TTL,
        },
    )

    identity_client: IdentityClientInterface
    if config.ENVIRONMENT in ["testing", "local"]:
        # disable testing
        identity_client = StubbedIdentityClient()
    else:
        identity_client = IdentityClient(
            http_endpoint=config.IDENTITY_SERVICE_HTTP_ENDPOINT,
            grpc_endpoint=config.IDENTITY_SERVICE_GRPC_ENDPOINT,
            session=ids_session,
        )

    capture_service = CaptureService(
        default_capture_delay_in_minutes=config.DEFAULT_CAPTURE_DELAY_IN_MINUTES
    )

    context = AppContext(
        log=root_logger,
        monitor=monitor,
        payout_maindb=payout_maindb,
        payout_bankdb=payout_bankdb,
        payin_maindb=payin_maindb,
        payin_paymentdb=payin_paymentdb,
        ledger_maindb=ledger_maindb,
        ledger_paymentdb=ledger_paymentdb,
        dsj_client=dsj_client,
        identity_client=identity_client,
        stripe_client=stripe_client,
        stripe_thread_pool=stripe_thread_pool,
        capture_service=capture_service,
        ids_session=ids_session,
        dsj_session=dsj_session,
    )

    # start monitoring
    monitor.start()

    context.log.debug("app context created")

    return context


def set_context_for_app(app: FastAPI, context: AppContext):
    assert "context" not in app.extra, "app context is already set"
    app.extra["context"] = cast(Any, context)


def get_context_from_app(app: FastAPI) -> AppContext:
    context = app.extra.get("context")
    assert context is not None, "app context is not set"
    assert isinstance(context, AppContext), "app context has correct type"
    return cast(AppContext, context)


def get_global_app_context(request: Request) -> AppContext:
    """
    Wrapper function so that client code does not need to make assumptions that context is tied to app.
    :param request:
    :return:
    """
    return get_context_from_app(request.app)


def app_context_exists(app: FastAPI) -> bool:
    context = app.extra.get("context")
    return context is not None


def remove_context_for_app(app: FastAPI, context: AppContext):
    app_context = app.extra.pop("context", None)
    assert app_context is not None, "app context is not set"
    assert app_context is context
