import asyncio
from math import ceil
from typing import List

import pytest
from sqlalchemy import text

from app.commons.context.app_context import AppContext
from app.commons.database.infra import DB
from app.commons.jobs.pool import JobPool
from app.commons.operational_flags import ENABLE_PAYIN_CONSUMER_PAYER_MIGRATION
from app.commons.types import PgpCode
from app.conftest import RuntimeSetter
from app.data_migration.payin import (
    BackfillPayerFromConsumer,
    ConsumerData,
    ExtractConsumers,
    LoadStripeCustomerToPayers,
)
from app.payin.core.payer.v1.processor import PayerProcessorV1
from app.payin.core.types import PayerReferenceIdType
from app.payin.models.maindb import partial_consumers
from app.payin.models.paymentdb import consumer_backfill_trackings, failed_consumers
from app.payin.repository.payer_repo import (
    GetPayerByPayerRefIdAndTypeInput,
    GetPgpCustomerInput,
    PayerRepository,
)
from app.payin.test_integration.maindb_data_factory import MainDBDataFactory
from app.payin.tests.utils import FunctionMock

pytestmark = [pytest.mark.asyncio]


class TestBackfillPayerFromConsumers:
    @pytest.fixture
    async def _prepared_consumers(
        self, maindb_data_factory: MainDBDataFactory
    ) -> List[MainDBDataFactory.ConsumerId]:
        return await maindb_data_factory.batch_prepare_consumers(num_of_consumer=10)

    async def test_extract_consumer_paged(
        self,
        mock_statsd_client,
        payin_maindb: DB,
        _prepared_consumers: List[MainDBDataFactory.ConsumerId],
    ):

        num_of_consumers_to_fetch = len(_prepared_consumers)
        offset = _prepared_consumers[0]

        extract_page_size = 3

        extract_consumers = ExtractConsumers(
            statsd=mock_statsd_client,
            payin_maindb=payin_maindb,
            consumer_table=partial_consumers,
            starting_point=offset,
            page_size=extract_page_size,
        )

        expected_pages = ceil(
            float(num_of_consumers_to_fetch) / float(extract_page_size)
        )

        extracted: List[ConsumerData] = []

        for i in range(1, expected_pages + 1):
            current_extracted = await extract_consumers.next_page()
            extracted += current_extracted

        assert not await extract_consumers.has_next()
        assert len(extracted) == num_of_consumers_to_fetch
        extracted_consumer_id = [consumer.id for consumer in extracted]
        assert set(extracted_consumer_id) == set(_prepared_consumers)

        extract_consumers = ExtractConsumers(
            statsd=mock_statsd_client,
            payin_maindb=payin_maindb,
            consumer_table=partial_consumers,
            starting_point=_prepared_consumers[-1] + 1,
            page_size=extract_page_size,
        )

        results = await extract_consumers.next_page()
        assert not results
        assert not await extract_consumers.has_next()

        extract_consumers = ExtractConsumers(
            statsd=mock_statsd_client,
            payin_maindb=payin_maindb,
            consumer_table=partial_consumers,
            starting_point=_prepared_consumers[0],
            page_size=len(_prepared_consumers) + 1,
        )

        results = await extract_consumers.next_page()
        assert len(results) == len(_prepared_consumers)
        extracted_consumer_id = [consumer.id for consumer in results]
        assert set(extracted_consumer_id) == set(_prepared_consumers)
        assert not await extract_consumers.has_next()

        extract_consumers = ExtractConsumers(
            statsd=mock_statsd_client,
            payin_maindb=payin_maindb,
            consumer_table=partial_consumers,
            starting_point=_prepared_consumers[0],
            page_size=len(_prepared_consumers),
        )

        results = await extract_consumers.next_page()
        assert len(results) == len(_prepared_consumers)
        extracted_consumer_id = [consumer.id for consumer in results]
        assert set(extracted_consumer_id) == set(_prepared_consumers)
        assert not await extract_consumers.has_next()

    async def test_extract_consumer_update_page_size(
        self,
        mock_statsd_client,
        payin_maindb: DB,
        _prepared_consumers: List[MainDBDataFactory.ConsumerId],
    ):
        num_of_consumers_to_fetch = len(_prepared_consumers)
        starting_point = _prepared_consumers[0]

        first_page_size = int(num_of_consumers_to_fetch / 3)
        second_page_size = num_of_consumers_to_fetch - first_page_size

        assert first_page_size, "first page should be non-zero"
        assert second_page_size, "second page should be non-zero"

        extract_consumers = ExtractConsumers(
            statsd=mock_statsd_client,
            payin_maindb=payin_maindb,
            consumer_table=partial_consumers,
            starting_point=starting_point,
            page_size=first_page_size,
        )

        assert extract_consumers.has_next()
        first_page_result = await extract_consumers.next_page()
        assert len(first_page_result) == first_page_size

        extract_consumers.page_size = second_page_size
        assert extract_consumers.has_next()
        second_page_result = await extract_consumers.next_page()
        assert len(second_page_result) == second_page_size

        two_pages_results: List[ConsumerData] = first_page_result + second_page_result
        two_pages_ids = set([cx.id for cx in two_pages_results])

        assert two_pages_ids == set(_prepared_consumers)

    async def test_transfer_and_load(
        self,
        mock_statsd_client,
        payin_maindb: DB,
        app_context: AppContext,
        payer_processor_v1: PayerProcessorV1,
        payer_repository: PayerRepository,
        _prepared_consumers: List[MainDBDataFactory.ConsumerId],
    ):

        extract_consumers = ExtractConsumers(
            statsd=mock_statsd_client,
            payin_maindb=payin_maindb,
            consumer_table=partial_consumers,
            starting_point=_prepared_consumers[0],
            page_size=len(_prepared_consumers),
        )

        results: List[ConsumerData] = await extract_consumers.next_page()

        for consumer_data in results:  # type: ConsumerData
            load = LoadStripeCustomerToPayers(
                statsd=mock_statsd_client,
                payin_paymentdb=app_context.payin_paymentdb,
                failed_consumer_table=failed_consumers,
                payer_processor=payer_processor_v1,
                record=consumer_data,
            )
            assert consumer_data.stripe_id
            filtered = await load.filter()
            assert filtered == consumer_data

            await load.execute()
            await self._verify_payer_by_consumer_data(
                consumer_data=consumer_data, payer_repository=payer_repository
            )

    async def test_transfer_and_load_with_failure(
        self,
        mock_statsd_client,
        payin_maindb: DB,
        app_context: AppContext,
        payer_processor_v1: PayerProcessorV1,
        payer_repository: PayerRepository,
        _prepared_consumers: List[MainDBDataFactory.ConsumerId],
    ):
        extract_consumers = ExtractConsumers(
            statsd=mock_statsd_client,
            payin_maindb=payin_maindb,
            consumer_table=partial_consumers,
            starting_point=_prepared_consumers[0],
            page_size=len(_prepared_consumers),
        )

        results: List[ConsumerData] = await extract_consumers.next_page()

        for consumer_data in results:  # type: ConsumerData
            load = LoadStripeCustomerToPayers(
                statsd=mock_statsd_client,
                payin_paymentdb=app_context.payin_paymentdb,
                failed_consumer_table=failed_consumers,
                payer_processor=payer_processor_v1,
                record=consumer_data,
            )

            load.payer_processor.backfill_payer = FunctionMock(  # type: ignore
                side_effect=Exception
            )

            await load.execute()
            await self._verify_failure_record_by_consumer_data(
                consumer_data=consumer_data, payin_paymentdb=app_context.payin_paymentdb
            )

    async def test_backfill_job(
        self,
        maindb_data_factory: MainDBDataFactory,
        app_context: AppContext,
        job_pool: JobPool,
        payer_repository: PayerRepository,
        mock_statsd_client,
        runtime_setter: RuntimeSetter,
    ):
        runtime_setter.set(ENABLE_PAYIN_CONSUMER_PAYER_MIGRATION, True)

        # 1. prepare 50 consumers record for "backfill"
        num_of_consumer_to_backfill = 50
        prepared_consumers = await maindb_data_factory.batch_prepare_consumers(
            num_of_consumer=num_of_consumer_to_backfill + 1
        )
        assert len(prepared_consumers) == num_of_consumer_to_backfill + 1

        # 2. insert a checkpoint to start from left most prepared consumer
        left_most_consumer_id: int = prepared_consumers[0]

        initial_checkpoint = await BackfillPayerFromConsumer._get_checkpoint(
            payin_paymentdb=app_context.payin_paymentdb,
            consumer_backfill_tracking_table=consumer_backfill_trackings,
        )

        assert (
            initial_checkpoint is not None
            and initial_checkpoint != left_most_consumer_id
        )

        await BackfillPayerFromConsumer._update_checkpoint(
            payin_paymentdb=app_context.payin_paymentdb,
            last_consumer_id=left_most_consumer_id,
            consumer_backfill_tracking_table=consumer_backfill_trackings,
        )

        last_processed_consumer_id = await BackfillPayerFromConsumer._get_checkpoint(
            payin_paymentdb=app_context.payin_paymentdb,
            consumer_backfill_tracking_table=consumer_backfill_trackings,
        )

        assert last_processed_consumer_id == left_most_consumer_id

        # 3. now run backfill job till end

        backfill_job = BackfillPayerFromConsumer(
            app_context=app_context,
            statsd_client=mock_statsd_client,
            job_pool=job_pool,
            consumer_table=partial_consumers,
            consumer_backfill_tracking_table=consumer_backfill_trackings,
        )

        assert not backfill_job.stop_event.is_set()
        await backfill_job.run()
        await job_pool.join()

        assert backfill_job.stop_event.is_set()

        # 4. now check our expectations
        # 4.1 last checkpoint
        expected_final_checkpoint_consumer_id = prepared_consumers[-1]
        assert (
            expected_final_checkpoint_consumer_id
            == await BackfillPayerFromConsumer._get_checkpoint(
                payin_paymentdb=app_context.payin_paymentdb,
                consumer_backfill_tracking_table=consumer_backfill_trackings,
            )
        )
        # 4.2 the left most prepared consumer shouldn't be back filled since it was used as a initial checkpoint
        assert not await payer_repository.get_payer_by_reference_id_and_type(
            GetPayerByPayerRefIdAndTypeInput(
                payer_reference_id_type=PayerReferenceIdType.DD_CONSUMER_ID,
                payer_reference_id=str(prepared_consumers[0]),
            )
        )

        # 4.3 all the rest prepared consumers should be properly back filled
        for consumer_id in prepared_consumers[1:]:
            await self._verify_payer_by_consumer_id(consumer_id, payer_repository)

    async def test_backfill_pause(
        self,
        maindb_data_factory: MainDBDataFactory,
        app_context: AppContext,
        job_pool: JobPool,
        payer_repository: PayerRepository,
        mock_statsd_client,
        runtime_setter: RuntimeSetter,
    ):
        runtime_setter.set(ENABLE_PAYIN_CONSUMER_PAYER_MIGRATION, True)
        # 1. prepare 50 consumers record for "backfill"
        num_of_consumer_to_backfill = 50
        prepared_consumers = await maindb_data_factory.batch_prepare_consumers(
            num_of_consumer=num_of_consumer_to_backfill + 1
        )
        assert len(prepared_consumers) == num_of_consumer_to_backfill + 1

        # 2. insert a checkpoint to start from left most prepared consumer
        left_most_consumer_id: int = prepared_consumers[0]

        initial_checkpoint = await BackfillPayerFromConsumer._get_checkpoint(
            payin_paymentdb=app_context.payin_paymentdb,
            consumer_backfill_tracking_table=consumer_backfill_trackings,
        )

        assert (
            initial_checkpoint is not None
            and initial_checkpoint != left_most_consumer_id
        )

        await BackfillPayerFromConsumer._update_checkpoint(
            payin_paymentdb=app_context.payin_paymentdb,
            last_consumer_id=left_most_consumer_id,
            consumer_backfill_tracking_table=consumer_backfill_trackings,
        )

        last_processed_consumer_id = await BackfillPayerFromConsumer._get_checkpoint(
            payin_paymentdb=app_context.payin_paymentdb,
            consumer_backfill_tracking_table=consumer_backfill_trackings,
        )

        assert last_processed_consumer_id == left_most_consumer_id

        # 3. now run backfill job till end

        backfill_job = BackfillPayerFromConsumer(
            app_context=app_context,
            statsd_client=mock_statsd_client,
            job_pool=job_pool,
            consumer_table=partial_consumers,
            consumer_backfill_tracking_table=consumer_backfill_trackings,
        )

        assert not backfill_job.stop_event.is_set()
        middle_consumer_id = prepared_consumers[int(len(prepared_consumers) / 2)]

        async def delay_set_stop():
            while not await payer_repository.get_payer_by_reference_id_and_type(
                GetPayerByPayerRefIdAndTypeInput(
                    payer_reference_id_type=PayerReferenceIdType.DD_CONSUMER_ID,
                    payer_reference_id=str(middle_consumer_id),
                )
            ):
                await asyncio.sleep(0.1)
            backfill_job.stop_event.set()

        await job_pool.spawn(delay_set_stop())
        await backfill_job.run()
        await job_pool.join()

        assert backfill_job.stop_event.is_set()

        # 4. now check our expectations
        # 4.1 last checkpoint should be smaller than middle consumer_id when stop event properly works
        last_checkpoint = await BackfillPayerFromConsumer._get_checkpoint(
            payin_paymentdb=app_context.payin_paymentdb,
            consumer_backfill_tracking_table=consumer_backfill_trackings,
        )
        assert last_checkpoint and middle_consumer_id >= last_checkpoint
        # 4.2 the left most prepared consumer shouldn't be back filled since it was used as a initial checkpoint
        assert not await payer_repository.get_payer_by_reference_id_and_type(
            GetPayerByPayerRefIdAndTypeInput(
                payer_reference_id_type=PayerReferenceIdType.DD_CONSUMER_ID,
                payer_reference_id=str(prepared_consumers[0]),
            )
        )

        # 4.3 all the rest prepared consumers should be properly back filled
        for consumer_id in [
            cx for cx in prepared_consumers[1:] if cx <= middle_consumer_id
        ]:
            await self._verify_payer_by_consumer_id(consumer_id, payer_repository)

    async def _verify_payer_by_consumer_id(
        self, consumer_id: int, payer_repository: PayerRepository
    ):
        payer = await payer_repository.get_payer_by_reference_id_and_type(
            GetPayerByPayerRefIdAndTypeInput(
                payer_reference_id=str(consumer_id),
                payer_reference_id_type=PayerReferenceIdType.DD_CONSUMER_ID,
            )
        )

        assert payer
        assert payer.payer_reference_id
        assert payer.payer_reference_id == str(consumer_id)
        assert payer.payer_reference_id_type == PayerReferenceIdType.DD_CONSUMER_ID

        pgp_customer = await payer_repository.get_pgp_customer(
            request=GetPgpCustomerInput(payer_id=payer.id, pgp_code=PgpCode.STRIPE)
        )
        assert pgp_customer

    async def _verify_payer_by_consumer_data(
        self, consumer_data: ConsumerData, payer_repository: PayerRepository
    ):

        payer = await payer_repository.get_payer_by_reference_id_and_type(
            GetPayerByPayerRefIdAndTypeInput(
                payer_reference_id=str(consumer_data.id),
                payer_reference_id_type=PayerReferenceIdType.DD_CONSUMER_ID,
            )
        )

        assert payer
        assert payer.payer_reference_id
        assert payer.payer_reference_id == str(consumer_data.id)
        assert payer.payer_reference_id_type == PayerReferenceIdType.DD_CONSUMER_ID
        assert payer.country == consumer_data.country_code

        pgp_customer = await payer_repository.get_pgp_customer(
            request=GetPgpCustomerInput(payer_id=payer.id, pgp_code=PgpCode.STRIPE)
        )

        assert pgp_customer.pgp_resource_id == consumer_data.stripe_id

    async def _verify_failure_record_by_consumer_data(
        self, consumer_data: ConsumerData, payin_paymentdb: DB
    ):
        stmt = text(f"select * from failed_consumer where id={consumer_data.id}")
        record = await payin_paymentdb.master().fetch_one(stmt)

        assert record
        assert record["id"] == consumer_data.id
        assert record["stripe_id"] == consumer_data.stripe_id
        assert record["stripe_country_id"] == consumer_data.stripe_country_id
