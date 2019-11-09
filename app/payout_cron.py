import asyncio
import os
import signal

from apscheduler.triggers.cron import CronTrigger

from app.commons.config.newrelic_loader import init_newrelic_agent

# ensure logger is loaded before newrelic init,
# so we don't reload the module and get duplicate log messages
from app.commons.context.logger import get_logger
from app.payout.jobs import MonitorTransfersWithIncorrectStatus

init_newrelic_agent()

from aiohttp import web

import pytz
from app.commons.jobs.scheduler import Scheduler
from doordash_python_stats.ddstats import doorstats_global, DoorStatsProxyMultiServer

from app.commons.instrumentation.pool import stat_resource_pool_jobs
from app.commons.jobs.pool import adjust_pool_sizes
from app.commons.jobs.startup_util import init_worker_resources
from app.commons.runtime import runtime

logger = get_logger("cron")


async def run_health_server(port: int = 80):
    """
    Starts a dumb web server used for k8s liveness probes

    :param port: Port on which web server runs
    :return:
    """

    async def handler(request):
        logger.info(
            "current payment-service release",
            release_tag=os.getenv("RELEASE_TAG", "unknown"),
        )
        return web.Response(text="OK")

    server = web.Server(handler)
    runner = web.ServerRunner(server)
    await runner.setup()
    logger.info(f"Starting health server on {port}")
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


def scheduler_heartbeat(statsd_client: DoorStatsProxyMultiServer) -> None:
    """
    Sends a heartbeat from the scheduler

    :param statsd_client: client to use to send heartbeat
    :return: None
    """
    statsd_client.incr("scheduler.heartbeat")


(app_config, app_context, stripe_pool) = init_worker_resources(pool_name="stripe")

scheduler = Scheduler()
scheduler.configure(timezone=pytz.UTC)  # all times will be interpreted in UTC timezone

loop = asyncio.get_event_loop()

app_context.monitor.add(
    stat_resource_pool_jobs(
        stat_prefix="resource.job_pools.payout",
        pool_name=stripe_pool.name,
        pool_job_stats=stripe_pool,
    ),
    interval_secs=app_config.MONITOR_INTERVAL_RESOURCE_JOB_POOL,
)


monitor_transfers_with_incorrect_status = MonitorTransfersWithIncorrectStatus(
    app_context=app_context, job_pool=stripe_pool
)
scheduler.add_job(
    func=monitor_transfers_with_incorrect_status.run,
    name=monitor_transfers_with_incorrect_status.job_name,
    trigger=CronTrigger(hour="7"),
)

scheduler.add_job(
    scheduler_heartbeat,
    trigger="cron",
    minute="*/1",
    kwargs={"statsd_client": doorstats_global},
)

scheduler.add_job(
    adjust_pool_sizes, trigger="cron", second="*/30", kwargs={"runtime": runtime}
)

scheduler.start()


async def handle_shutdown():
    logger.info("Received scheduler shutdown request")
    scheduler.shutdown()
    count, _results = await stripe_pool.cancel()
    logger.info("Cancelled stripe pool", count=count)
    loop.stop()
    logger("Done shutting down!")


# Run health server in background
loop.create_task(run_health_server())

loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(handle_shutdown()))

print("Press Ctrl+{0} to exit".format("Break" if os.name == "nt" else "C"))

loop.run_forever()
