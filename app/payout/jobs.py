from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from uuid import uuid4
from structlog import BoundLogger

from app.commons.context.app_context import AppContext
from app.commons.context.logger import get_logger
from app.commons.context.req_context import ReqContext, build_req_context
from app.commons.jobs.pool import JobPool
from app.payout.repository.maindb.transfer import TransferRepository

logger = get_logger("jobs")


class JobInstanceContext:
    """
    A JobInstanceContext is built per each time when a job instance is triggered by scheduler
    """

    app_context: AppContext
    job_pool: JobPool
    job_instance_id: str
    job_name: str
    log: BoundLogger

    def __init__(self, app_context: AppContext, job_pool: JobPool, job_name: str):
        self.app_context = app_context
        self.job_pool = job_pool
        self.job_name = job_name
        self.job_instance_id = str(uuid4())
        self.log = app_context.log.bind(
            job_instance_id=self.job_instance_id, job_name=self.job_name
        )

    def build_req_context(self) -> ReqContext:
        """
        Build a request context with logger bind with job_name and job_instance_id
        :return:
        """
        return build_req_context(
            self.app_context,
            job_name=self.job_name,
            job_instance_id=self.job_instance_id,
        )


class Job(ABC):
    """
    Encapsulate a defined Job.
    An instance of a Job is callable that can be invoked by scheduler.
    """

    app_context: AppContext
    job_pool: JobPool

    def __init__(self, *, app_context: AppContext, job_pool: JobPool):
        self.app_context = app_context
        self.job_pool = job_pool

    @property
    @abstractmethod
    def job_name(self) -> str:
        pass

    @abstractmethod
    async def _trigger(self, job_instance_cxt: JobInstanceContext):
        """
        Sub class should implement trigger logic which will be invoked at each time this job being triggered by scheduler
        :param job_instance_cxt:
        :return:
        """
        raise NotImplementedError("sub class must implement this method!")

    async def run(self):
        """
        Actually trigger and run a new instance defined by this job.
        - Each run will assign a unique job_instance_id for the newly created job instance
        - When add a job to scheduler, need to do
            ```
            scheduler.add_job(somejob.run, ...)
            ```
          to provider scheduler a "coroutine function" to invoke
        :return:
        """
        jon_instance_cxt: JobInstanceContext = JobInstanceContext(
            app_context=self.app_context, job_pool=self.job_pool, job_name=self.job_name
        )
        jon_instance_cxt.log.info("Triggering job instance")
        await self._trigger(jon_instance_cxt)
        jon_instance_cxt.log.info("Triggered job instance")


async def job_callback(res, err, ctx):
    if err:
        logger.error(
            "Exception running job", exc_info=err[0]
        )  # err = (exec, traceback)
    else:
        logger.debug("Job successfully completed")


class MonitorTransfersWithIncorrectStatus(Job):
    @property
    def job_name(self) -> str:
        return "MonitorTransfersWithIncorrectStatus"

    async def _trigger(self, job_instance_cxt: JobInstanceContext):
        # Create a window of the last 7 days
        start = self._start_of_the_week(date=datetime.utcnow()) - timedelta(weeks=1)

        transfer_repo = TransferRepository(
            database=job_instance_cxt.app_context.payout_maindb
        )
        transfer_ids = await transfer_repo.get_transfers_by_submitted_at_and_method(
            start_time=start
        )

        job_instance_cxt.log.info(
            "[monitor_transfers_with_incorrect_status] Starting execution",
            start_time=start,
            transfers_total_number=len(transfer_ids),
        )
        # todo: complete logic after the processor is updated

    def _start_of_the_week(self, date: datetime) -> datetime:
        return date - timedelta(days=date.weekday())
