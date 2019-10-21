import newrelic.agent
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from apscheduler.util import undefined


class Scheduler(AsyncIOScheduler):
    def add_job(
        self,
        func,
        trigger=None,
        args=None,
        kwargs=None,
        id=None,
        name=None,
        misfire_grace_time=undefined,
        coalesce=undefined,
        max_instances=undefined,
        next_run_time=undefined,
        jobstore="default",
        executor="default",
        replace_existing=False,
        **trigger_args
    ):
        # todo PAYIN-126 temporarily disable NR here for further investigation on
        # runtime error happened since 10/12 https://sentry.io/share/issue/22c311ab907b45e0b05d3fc71bd3c90b/
        background_task = newrelic.agent.BackgroundTaskWrapper(func)
        return super().add_job(
            background_task,
            trigger=trigger,
            args=args,
            kwargs=kwargs,
            id=id,
            name=name,
            misfire_grace_time=misfire_grace_time,
            coalesce=coalesce,
            max_instances=max_instances,
            next_run_time=next_run_time,
            jobstore=jobstore,
            executor=executor,
            replace_existing=replace_existing,
            **trigger_args
        )
