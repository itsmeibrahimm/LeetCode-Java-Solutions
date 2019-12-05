import asyncio
import logging
import signal
import uuid

from aiokafka import AIOKafkaConsumer
from asyncio_pool import AioPool
from typing import Awaitable, Callable, List

from app.commons.context.app_context import AppContext
from app.commons.context.logger import set_request_id

log = logging.getLogger(__name__)


class KafkaMessageConsumer:
    app_context: AppContext
    topic_name: str

    def __init__(
        self,
        *,
        app_context: AppContext,
        kafka_url: str,
        topic_name: str,
        processor: Callable[[AppContext, str], Awaitable[bool]],
    ):
        super().__init__()
        self.app_context = app_context
        self.processor = processor
        self.topic_name = topic_name
        self.kafka_url = kafka_url
        consumer_group = f"{topic_name}-group"

        log.info("starting consumer...")
        self.consumer = AIOKafkaConsumer(
            self.topic_name,
            loop=asyncio.get_running_loop(),
            bootstrap_servers=kafka_url,
            group_id=consumer_group,  # Consumer must be in a group to commit
            enable_auto_commit=True,  # Is True by default anyway
            auto_commit_interval_ms=10000,  # Autocommit every 10 second
            auto_offset_reset="earliest",  # If committed offset not found, start from beginning
        )

    async def run(self):
        try:
            set_request_id(uuid.uuid4())
            await self.consumer.start()
            async for msg in self.consumer:  # Will periodically commit returned messages.
                log.debug("message processing starting")
                await self.processor(self.app_context, msg.value)
                log.debug("message processing complete")
        except asyncio.CancelledError as e:
            log.error("consumer was cancelled mid-execution", exc_info=e)
        except Exception as e:
            log.error("message processing failed", exc_info=e)
        finally:
            # consumer connection check is done in aiokafka
            await self.consumer.stop()
        log.info("consumer stopping")

    async def stop(self):
        try:
            # consumer connection check is done in aiokafka
            await self.consumer.stop()
            log.info("consumer stopped")
        except Exception as e:
            log.error("consumer failed to stop", exc_info=e)


class KafkaWorker:
    app_context: AppContext
    pool: AioPool
    stop_producing_event: asyncio.Event
    consumers: List[KafkaMessageConsumer]
    kafka_url: str
    topic_name: str

    def __init__(
        self,
        *,
        app_context: AppContext,
        topic_name: str,
        kafka_url: str,
        processor: Callable[[AppContext, str], Awaitable[bool]],
        num_consumers: int,
    ):
        self.app_context = app_context
        self.pool = AioPool(size=num_consumers + 1)
        self.stop_producing_event = asyncio.Event()
        self.topic_name = topic_name
        self.kafka_url = kafka_url

        self.consumers = [
            KafkaMessageConsumer(
                app_context=self.app_context,
                kafka_url=kafka_url,
                topic_name=topic_name,
                processor=processor,
            )
            for _ in range(num_consumers)
        ]

    async def run(self):
        curr_loop = asyncio.get_running_loop()
        curr_loop.add_signal_handler(signal.SIGTERM, self.handle_signal)
        curr_loop.add_signal_handler(signal.SIGINT, self.handle_signal)

        log.info("starting worker")

        await self.start()
        log.debug("worker started")

        await self.pool.join()
        log.info("worker stopped gracefully")

    def handle_signal(self):
        asyncio.create_task(self.stop())

    async def start(self):
        log.debug("starting worker consumers...")
        for consumer in self.consumers:
            log.debug("starting worker consumer")
            await self.pool.spawn(consumer.run())

    async def stop(self, graceful_timeout_seconds: int = 10):
        if self.stop_producing_event.is_set() or graceful_timeout_seconds <= 0:
            log.info("worker stop issued - force quit")
            return await self.pool.cancel()

        log.info("worker stop issued")
        self.stop_producing_event.set()
        await asyncio.sleep(graceful_timeout_seconds)
        for consumer in self.consumers:
            log.debug("stopping worker consumer")
            await consumer.stop()

        await self.pool.cancel()
