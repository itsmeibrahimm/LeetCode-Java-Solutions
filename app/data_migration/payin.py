import asyncio
from typing import List, Optional

from doordash_python_stats.ddstats import DoorStatsProxyMultiServer
from sqlalchemy import asc, select

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import ReqContext
from app.commons.database.infra import DB
from app.commons.database.model import DBEntity
from app.commons.jobs.pool import JobPool
from app.commons.operational_flags import (
    ENABLE_PAYIN_CONSUMER_PAYER_MIGRATION,
    PAYIN_CONSUMER_PAYER_MIGRATION_EXTRACT_PAGE_SIZE,
)
from app.commons.runtime import runtime
from app.commons.types import CountryCode
from app.commons.utils.legacy_utils import get_country_code_by_id
from app.commons.utils.validation import not_none
from app.data_migration.base import ExtractedRecord, ExtractMany, TransformAndLoadOne
from app.jobs.model import Job, JobInstanceContext
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payer.v1.processor import PayerProcessorV1
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.core.types import PayerReferenceIdType
from app.payin.models.maindb import PartialConsumerTable
from app.payin.models.paymentdb import (
    consumer_backfill_trackings,
    ConsumerBackfillTrackingTable,
    failed_consumers,
    FailedConsumerTable,
)
from app.payin.repository.payer_repo import PayerRepository
from app.payin.repository.payment_method_repo import PaymentMethodRepository


class ConsumerData(DBEntity, ExtractedRecord):
    id: int
    stripe_id: Optional[str]
    stripe_country_id: int

    @property
    def country_code(self) -> CountryCode:
        return get_country_code_by_id(self.stripe_country_id)


class ExtractConsumers(ExtractMany[ConsumerData]):
    """
    A wrapper of paginated query which extracts certain numbers of rows from maindb.consumer table per paged call.
    """

    payin_maindb: DB
    consumers: PartialConsumerTable
    starting_point: Optional[int]
    page_size: int

    def __init__(
        self,
        statsd: DoorStatsProxyMultiServer,
        payin_maindb: DB,
        consumer_table: PartialConsumerTable,
        starting_point: int = -1,
        page_size: int = 10,
    ):
        """

        Args:
            statsd (): statsd client
            payin_maindb (): maindb connections
            consumer_table (): consumer table schema
            starting_point (): starting point (inclusive) to select data
            page_size (): per page size
        """
        super().__init__(statsd)
        self.payin_maindb = payin_maindb
        self.consumers = consumer_table
        self.starting_point = starting_point
        self.page_size = page_size

    async def do_query(self) -> List[ConsumerData]:

        if await self.has_next():
            stmt = (
                select(
                    [
                        self.consumers.id,
                        self.consumers.stripe_id,
                        self.consumers.stripe_country_id,
                    ]
                )
                .where(self.consumers.id >= self.starting_point)
                .order_by(asc(self.consumers.id))
                .limit(self.page_size + 1)
            )

            rows = await self.payin_maindb.replica().fetch_all(stmt)

            if len(rows) > self.page_size:
                self.starting_point = rows[-1][self.consumers.id]
                return [ConsumerData.from_row(r) for r in rows[:-1]]
            else:
                self.starting_point = None
                return [ConsumerData.from_row(r) for r in rows]

        return []

    async def has_next(self) -> bool:
        return self.starting_point is not None


class LoadStripeCustomerToPayers(TransformAndLoadOne[ConsumerData]):
    """
    Transform maindb.consumer.id, stripe_id and stripe_country_id into proper payer data,
    then backfill as payer and pgp_customer into payment db
    """

    payin_paymentdb: DB
    failed_consumers: FailedConsumerTable
    payer_processor: PayerProcessorV1

    def __init__(
        self,
        statsd: DoorStatsProxyMultiServer,
        record: ConsumerData,
        payin_paymentdb: DB,
        failed_consumer_table: FailedConsumerTable,
        payer_processor: PayerProcessorV1,
    ):
        """

        Args:
            statsd (): statsd client
            record (): one single consumer data to process
            payin_paymentdb (): payment db connection
            failed_consumer_table (): tracking table for consumer which was failed to process
            payer_processor (): payer processor
        """
        super().__init__(statsd, record)
        self.payin_paymentdb = payin_paymentdb
        self.failed_consumers = failed_consumer_table
        self.payer_processor = payer_processor

    async def transform_and_load(self, record: ConsumerData):

        try:
            await self.payer_processor.backfill_payer(
                payer_reference_id_type=PayerReferenceIdType.DD_CONSUMER_ID,
                payer_reference_id=str(record.id),
                pgp_customer_id=not_none(record.stripe_id),
                country=record.country_code,
            )
        except Exception:
            self.log.warn("inserting failed consumer record", **record.dict())
            await LoadStripeCustomerToPayers.insert_failed_consumer_record(
                record, self.payin_paymentdb, self.failed_consumers
            )
            self.log.warn("inserted failed consumer record", **record.dict())
            raise

    async def filter(self) -> Optional[ConsumerData]:
        """
        if this consumer doesn't have stripe_id then skip processing
        since it means no attempts of creating stripe customer was made for this consumer
        """
        if self.record.stripe_id and len(self.record.stripe_id) > 1:
            return self.record
        return None

    @staticmethod
    async def insert_failed_consumer_record(
        record: ConsumerData,
        payin_paymentdb: DB,
        failed_consumer_table: FailedConsumerTable,
    ):
        stmt = failed_consumer_table.table.insert().values(
            {
                failed_consumer_table.id: record.id,
                failed_consumer_table.stripe_id: record.stripe_id,
                failed_consumer_table.stripe_country_id: record.stripe_country_id,
            }
        )
        await payin_paymentdb.master().execute(stmt)


class BackfillPayerFromConsumer(Job):
    """
    Cron job to backfill payer from maindb.consumer table
    """

    default_extract_page_size = 10
    consumer_table: PartialConsumerTable
    consumer_backfill_tracking_table: ConsumerBackfillTrackingTable
    stop_event: asyncio.Event

    def __init__(
        self,
        *,
        app_context: AppContext,
        job_pool: JobPool,
        statsd_client: DoorStatsProxyMultiServer,
        consumer_table: PartialConsumerTable,
        consumer_backfill_tracking_table: ConsumerBackfillTrackingTable,
        default_extract_page_size: int = 10,
    ):
        super().__init__(
            app_context=app_context, job_pool=job_pool, statsd_client=statsd_client
        )
        self.consumer_table = consumer_table
        self.consumer_backfill_tracking_table = consumer_backfill_tracking_table
        self.default_extract_page_size = default_extract_page_size
        self.stop_event = asyncio.Event()

    async def _trigger(self, job_instance_cxt: JobInstanceContext):

        if self._should_stop():
            job_instance_cxt.log.info("Finished or stopped. Noop and return!")
            return

        last_processed_consumer_id = await BackfillPayerFromConsumer._get_checkpoint(
            payin_paymentdb=job_instance_cxt.app_context.payin_paymentdb,
            consumer_backfill_tracking_table=self.consumer_backfill_tracking_table,
        )

        if last_processed_consumer_id and last_processed_consumer_id < 0:
            self.stop_event.set()
            job_instance_cxt.log.info("Stop as there is no more record to process")
            return

        starting_point_consumer_id = not_none(last_processed_consumer_id) + 1
        extract_consumers = ExtractConsumers(
            statsd=self._statsd_client,
            payin_maindb=job_instance_cxt.app_context.payin_maindb,
            consumer_table=self.consumer_table,
            starting_point=starting_point_consumer_id,
            page_size=self.get_extract_page_size(),
        )

        await self._batch_etl(extract_consumers, job_instance_cxt=job_instance_cxt)

    async def _batch_etl(
        self, extract_consumers: ExtractConsumers, job_instance_cxt: JobInstanceContext
    ):
        async def job_callback(res, err, ctx):
            if err:
                job_instance_cxt.log.error(
                    "Exception running job", exc_info=err[0]
                )  # err = (exec, traceback)
            else:
                job_instance_cxt.log.debug("Job successfully completed")

        while await extract_consumers.has_next():
            # first switch check: if should stop, then avoid pulling data from maindb

            if self._should_stop():
                job_instance_cxt.log.warn(
                    "stop signal received. short cut current batch"
                )
                return

            # update page size from runtime
            extract_consumers.page_size = self.get_extract_page_size()
            records = await extract_consumers.next_page()

            for record in records:
                # second switch check: if should stop, avoid insert record to payment db
                if self._should_stop():
                    job_instance_cxt.log.warn(
                        "stop signal received, short cut current batch",
                        next_consumer_id=record.id,
                    )
                    return
                load = LoadStripeCustomerToPayers(
                    record=record,
                    payin_paymentdb=job_instance_cxt.app_context.payin_paymentdb,
                    failed_consumer_table=failed_consumers,
                    payer_processor=BackfillPayerFromConsumer.build_payer_processor(
                        job_instance_cxt.app_context,
                        job_instance_cxt.build_req_context(),
                    ),
                    statsd=self._statsd_client,
                )
                # temporary heck to avoid race condition when sibling level queries attempting to acquire
                # same connection for transaction. due to the way we implement transaction
                # stacking and connection context var caching
                await asyncio.sleep(0.02)
                await job_instance_cxt.job_pool.spawn(load.execute(), cb=job_callback)

            last_consumer_id = records[-1].id if records else -1
            job_instance_cxt.log.info(
                "Saving last processed consumer id in batch",
                consumer_id=last_consumer_id,
            )
            await BackfillPayerFromConsumer._update_checkpoint(
                payin_paymentdb=job_instance_cxt.app_context.payin_paymentdb,
                last_consumer_id=last_consumer_id,
                consumer_backfill_tracking_table=self.consumer_backfill_tracking_table,
            )
        if not self.stop_event.is_set():
            self.stop_event.set()

    def _should_stop(self):
        if runtime.get_bool(ENABLE_PAYIN_CONSUMER_PAYER_MIGRATION, False):
            # if enabled check stop event
            return self.stop_event.is_set()

        # not enabled
        if not self.stop_event.is_set():
            self.stop_event.set()
        return True

    def get_extract_page_size(self) -> int:
        return runtime.get_int(
            PAYIN_CONSUMER_PAYER_MIGRATION_EXTRACT_PAGE_SIZE,
            self.default_extract_page_size,
        )

    @staticmethod
    async def _update_checkpoint(
        payin_paymentdb: DB,
        last_consumer_id: int,
        consumer_backfill_tracking_table: ConsumerBackfillTrackingTable,
    ):
        stmt = (
            consumer_backfill_trackings.table.update()
            .where(consumer_backfill_tracking_table.id == 1)
            .values({consumer_backfill_tracking_table.consumer_id: last_consumer_id})
        )

        await payin_paymentdb.master().execute(stmt)

    @staticmethod
    async def _get_checkpoint(
        payin_paymentdb: DB,
        consumer_backfill_tracking_table: ConsumerBackfillTrackingTable,
    ) -> Optional[int]:
        stmt = consumer_backfill_tracking_table.table.select().where(
            consumer_backfill_tracking_table.id == 1
        )

        row = await payin_paymentdb.master().fetch_one(stmt)

        if not row:
            insert_dummy = (
                consumer_backfill_tracking_table.table.insert()
                .values(
                    {
                        consumer_backfill_tracking_table.id: 1,
                        consumer_backfill_tracking_table.consumer_id: 0,
                    }
                )
                .returning(*consumer_backfill_tracking_table.table.columns.values())
            )
            row = await payin_paymentdb.master().fetch_one(insert_dummy)

        return not_none(row)[consumer_backfill_tracking_table.consumer_id]

    @staticmethod
    def build_payer_processor(
        app_context: AppContext, req_context: ReqContext
    ) -> PayerProcessorV1:

        payment_method_repository: PaymentMethodRepository = PaymentMethodRepository(
            app_context
        )

        payer_repository: PayerRepository = PayerRepository(app_context)

        payment_method_client: PaymentMethodClient = PaymentMethodClient(
            app_ctxt=app_context,
            payment_method_repo=payment_method_repository,
            stripe_async_client=req_context.stripe_async_client,
            log=req_context.log,
        )

        payer_client: PayerClient = PayerClient(
            app_ctxt=app_context,
            payer_repo=payer_repository,
            stripe_async_client=req_context.stripe_async_client,
            log=req_context.log,
        )

        payer_processor: PayerProcessorV1 = PayerProcessorV1(
            payment_method_client=payment_method_client,
            payer_client=payer_client,
            log=req_context.log,
        )

        return payer_processor

    @property
    def job_name(self) -> str:
        return "BackfillPayerFromConsumer"
