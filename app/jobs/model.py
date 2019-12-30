from abc import ABC, abstractmethod
from typing import Dict, Optional, Union
from uuid import uuid4

from doordash_python_stats.ddstats import DoorStatsProxyMultiServer
from structlog import BoundLogger

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context, ReqContext
from app.commons.jobs.pool import JobPool


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
    _statsd_client: DoorStatsProxyMultiServer

    def __init__(
        self,
        *,
        app_context: AppContext,
        job_pool: JobPool,
        statsd_client: DoorStatsProxyMultiServer,
    ):
        self.app_context = app_context
        self.job_pool = job_pool
        self._statsd_client = statsd_client

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

    def _stats_tag(self) -> Dict[str, str]:
        return {"job": self.job_name}

    async def stats_incr(
        self, *, metric_name: str, tags: Optional[Dict[str, str]] = None
    ):
        all_tags = self._stats_tag()
        if tags:
            all_tags.update(tags)

        self._statsd_client.incr(metric_name, tags=all_tags)

    async def stats_gauge(
        self,
        *,
        metric_name: str,
        value: Union[int, float],
        tags: Optional[Dict[str, str]] = None,
    ):
        all_tags = self._stats_tag()
        if tags:
            all_tags.update(tags)
        self._statsd_client.gauge(metric_name, value, tags=all_tags)

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
        await self.stats_incr(metric_name="job-trigger-start")
        jon_instance_cxt.log.info("Triggering job instance")
        await self._trigger(jon_instance_cxt)
        await self.stats_incr(metric_name="job-trigger-finish")
        jon_instance_cxt.log.info("Triggered job instance")
