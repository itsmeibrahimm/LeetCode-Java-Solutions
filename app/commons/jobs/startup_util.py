import asyncio
from typing import Tuple

from app.commons.config.app_config import AppConfig
from app.commons.context.app_context import AppContext, create_app_context
from app.commons.context.logger import init_logger
from app.commons.instrumentation import sentry
from app.commons.jobs.pool import JobPool
from app.commons.stats import init_global_statsd

logger = init_logger


def init_worker_resources(
    app_config: AppConfig, pool_name: str, pool_size: int
) -> Tuple[AppContext, JobPool]:
    """

    :return: a tuple containing the app config, a pared version of the web app_context and a job pool for executing
    tasks
    """
    if app_config.SENTRY_CONFIG:
        sentry.init_sentry_sdk(app_config.SENTRY_CONFIG)

    # set up global statsd
    init_global_statsd(
        prefix=app_config.GLOBAL_STATSD_PREFIX,
        host=app_config.STATSD_SERVER,
        fixed_tags={"env": app_config.ENVIRONMENT},
    )

    loop = asyncio.get_event_loop()
    app_context = loop.run_until_complete(create_app_context(app_config))

    if pool_size > app_config.STRIPE_MAX_WORKERS:
        logger.error(
            "AioJobPool size is larger than stripe concurrent worker size",
            pool_name=pool_name,
            pool_size=pool_size,
            stripe_max_worker=app_config.STRIPE_MAX_WORKERS,
        )
        pool_size = app_config.STRIPE_MAX_WORKERS

    # syncing stripe client pool with jobpool to achieve optimal concurrency
    job_pool = JobPool.create_pool(size=pool_size, name=pool_name)

    return app_context, job_pool
