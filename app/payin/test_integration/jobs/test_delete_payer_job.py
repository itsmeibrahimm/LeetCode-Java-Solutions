import uuid
from datetime import datetime
from pytz import timezone
from unittest.mock import MagicMock

import pytest
from asynctest import create_autospec, patch

from app.commons.context.app_context import AppContext
from app.commons.jobs.pool import JobPool
from app.payin.core.payer.types import DeletePayerRequestStatus
from app.payin.core.payer.v0.processor import DeletePayerProcessor
from app.payin.jobs.delete_payer_job import DeletePayer
from app.payin.repository.payer_repo import (
    PayerRepository,
    DeletePayerRequestDbEntity,
    FindDeletePayerRequestByStatusInput,
)


@pytest.fixture
def delete_payer_job_pool() -> JobPool:
    return JobPool(name="test_delete_payer_job_pool")


class TestDeletePayerJob:
    @pytest.mark.asyncio
    @patch(
        "app.payin.jobs.delete_payer_job.enable_delete_payer_processing",
        return_value=True,
    )
    @patch(
        "app.payin.jobs.delete_payer_job.PayerRepository",
        return_value=create_autospec(PayerRepository),
    )
    @patch(
        "app.payin.jobs.delete_payer_job.DeletePayerProcessor",
        return_value=create_autospec(DeletePayerProcessor),
    )
    async def test_delete_payer_when_none_exists(
        self,
        mock_delete_payer_processor,
        mock_payer_repository,
        mock_enable_delete_payer_processing,
        app_context: AppContext,
        delete_payer_job_pool: JobPool,
    ):
        job_instance = DeletePayer(
            app_context=app_context,
            job_pool=delete_payer_job_pool,
            statsd_client=MagicMock(),
        )
        await job_instance.run()
        await delete_payer_job_pool.join()
        mock_payer_repository.return_value.find_delete_payer_requests_by_status.assert_called_once_with(
            find_delete_payer_request_by_status_input=FindDeletePayerRequestByStatusInput(
                status=DeletePayerRequestStatus.IN_PROGRESS
            )
        )
        mock_delete_payer_processor.return_value.delete_payer.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        "app.payin.jobs.delete_payer_job.enable_delete_payer_processing",
        return_value=True,
    )
    @patch(
        "app.payin.jobs.delete_payer_job.PayerRepository",
        return_value=create_autospec(PayerRepository),
    )
    @patch(
        "app.payin.jobs.delete_payer_job.DeletePayerProcessor",
        return_value=create_autospec(DeletePayerProcessor),
    )
    async def test_delete_payer_when_one_exists(
        self,
        mock_delete_payer_processor,
        mock_payer_repository,
        mock_enable_delete_payer_processing,
        app_context: AppContext,
        delete_payer_job_pool: JobPool,
    ):
        delete_payer_request = DeletePayerRequestDbEntity(
            id=uuid.uuid4(),
            client_request_id=uuid.uuid4(),
            consumer_id=123,
            payer_id=None,
            status=DeletePayerRequestStatus.IN_PROGRESS.value,
            summary="",
            retry_count=0,
            created_at=datetime.now(timezone("UTC")),
            updated_at=datetime.now(timezone("UTC")),
            acknowledged=False,
        )

        async def mock_find_delete_payer_requests_by_status(*args, **kwargs):
            return [delete_payer_request]

        mock_payer_repository.return_value.find_delete_payer_requests_by_status = (
            mock_find_delete_payer_requests_by_status
        )

        job_instance = DeletePayer(
            app_context=app_context,
            job_pool=delete_payer_job_pool,
            statsd_client=MagicMock(),
        )
        await job_instance.run()
        await delete_payer_job_pool.join()
        mock_delete_payer_processor.return_value.delete_payer.assert_called_once_with(
            delete_payer_request
        )
