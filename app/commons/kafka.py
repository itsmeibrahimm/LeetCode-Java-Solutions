import asyncio
import logging
import signal
import uuid

from asyncio_pool import AioPool
from confluent_kafka import Consumer
from typing import Awaitable, Callable, List

from app.commons.context.app_context import AppContext
from app.commons.context.logger import set_request_id

log = logging.getLogger(__name__)


class KafkaMessageConsumer:
    app_context: AppContext
    topic_name: str
    stop_consuming_event: asyncio.Event

    def __init__(
        self,
        *,
        app_context: AppContext,
        kafka_url: str,
        topic_name: str,
        processor: Callable[[AppContext, str], Awaitable[bool]],
        stop_consuming_event: asyncio.Event,
    ):
        super().__init__()
        self.app_context = app_context
        self.processor = processor
        self.topic_name = topic_name
        self.kafka_url = kafka_url
        self.stop_consuming_event = stop_consuming_event
        consumer_group = f"payment-service-{topic_name}-task-consumer"

        log.info("starting consumer...")
        self.consumer = Consumer(
            {
                "bootstrap.servers": kafka_url,
                "group.id": consumer_group,  # Consumer must be in a group to commit
                "auto.offset.reset": "earliest",  # If committed offset not found, start from beginning
                "enable.auto.commit": True,
                "auto.commit.interval.ms": (10 * 1000),  # Autocommit every 10 second
                "fetch.min.bytes": 1,
                "fetch.message.max.bytes": (1024 * 1024),
                "session.timeout.ms": (10 * 1000),
                "heartbeat.interval.ms": (3 * 1000),
                "max.poll.interval.ms": (5 * 60 * 1000),
            }
        )

    async def run(self):
        try:
            set_request_id(uuid.uuid4())
            self.consumer.subscribe([self.topic_name])
            while not self.stop_consuming_event.is_set():
                loop = asyncio.get_event_loop()
                msg = await loop.run_in_executor(None, self.read_next_task)

                if msg is None:
                    continue
                if msg.error():
                    log.warning("Consumer error.", extra={"error": msg.error()})
                    continue

                log.debug(f"message processing starting")
                await self.processor(self.app_context, msg.value().decode())
                log.debug("message processing complete")
        except asyncio.CancelledError as e:
            log.error("consumer was cancelled mid-execution", exc_info=e)
        except Exception as e:
            log.error("message processing failed", exc_info=e)
        finally:
            # consumer connection check is done in aiokafka
            await self.consumer.close()
        log.info("consumer stopping")

    def read_next_task(self):
        return self.consumer.poll(1.0)

    async def stop(self):
        try:
            # consumer connection check is done in aiokafka
            await self.consumer.close()
            log.info("consumer stopped")
        except Exception as e:
            log.error("consumer failed to stop", exc_info=e)


class KafkaWorker:
    app_context: AppContext
    pool: AioPool
    stop_consuming_event: asyncio.Event
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
        self.stop_consuming_event = asyncio.Event()
        self.topic_name = topic_name
        self.kafka_url = kafka_url

        self.consumers = [
            KafkaMessageConsumer(
                app_context=self.app_context,
                kafka_url=kafka_url,
                topic_name=topic_name,
                processor=processor,
                stop_consuming_event=self.stop_consuming_event,
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
        if self.stop_consuming_event.is_set() or graceful_timeout_seconds <= 0:
            log.info("worker stop issued - force quit")
            return await self.pool.cancel()

        log.info("worker stop issued")
        self.stop_consuming_event.set()
        await asyncio.sleep(graceful_timeout_seconds)

        await self.pool.cancel()
