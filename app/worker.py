# ensure logger is loaded before newrelic init,
# so we don't reload the module and get duplicate log messages
from app.commons.config.utils import init_app_config_for_payout_worker
from app.commons.context.app_context import create_app_context
from app.commons.context.logger import get_logger
from app.commons.config.newrelic_loader import init_newrelic_agent
from app.commons.kafka import KafkaWorker
from app.commons.worker_health_server import HealthServer

init_newrelic_agent()

import argparse
import asyncio
import importlib
import typing

from app.commons.stats import init_global_statsd


"""
TODO:
* static definition of events to message processors
* parsing task message body --> mapping to handler / processor
* error handling for failed messages (log error / retry?)
* add monitoring for threadpool stats
* define the message body serialization and format
* add the kafka client to app_context for publishing messages
DONE:
* graceful shutdown on SIGTERM
"""
log = get_logger("worker")


async def main(topic_name: str, processor, number_consumers: int):
    app_config = init_app_config_for_payout_worker()

    health_server = HealthServer()
    await health_server.start(port=app_config.WORKER_HEALTH_SERVER_PORT)

    init_global_statsd(
        prefix=app_config.GLOBAL_STATSD_PREFIX,
        host=app_config.STATSD_SERVER,
        fixed_tags={"env": app_config.ENVIRONMENT},
    )

    app_context = await create_app_context(app_config)

    worker = KafkaWorker(
        app_context=app_context,
        app_config=app_config,
        topic_name=topic_name,
        processor=processor,
        num_consumers=number_consumers,
    )
    await worker.run()

    await health_server.stop()

    await app_context.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--topic_name", "-t", type=str, required=True)
    p.add_argument("--processor", "-p", type=str, required=True)
    p.add_argument("--num_consumers", "-c", type=int, required=True)
    args = p.parse_args()

    processor: typing.Any = importlib.import_module(args.processor)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        main(args.topic_name, processor.process_message, args.num_consumers)
    )
