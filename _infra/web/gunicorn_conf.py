import os
import multiprocessing
from concurrent.futures import ThreadPoolExecutor


loglevel = "info"
workers = 2
bind = "0.0.0.0:80"
keepalive = 120
errorlog = "-"
proc_name = "payment-service"
max_requests = 10000
max_requests_jitter = 500


def post_fork(server, worker):
    import newrelic.agent
    import newrelic.core

    from app.commons.config.newrelic import create_new_relic_config

    environment = os.environ.get("ENVIRONMENT", "unknown")

    # new relic config
    config = create_new_relic_config(environment)
    settings = newrelic.agent.global_settings()

    # set the license key for the newrelic agent
    settings.license_key = config.NEW_RELIC_LICENSE_KEY.value

    # and then initialize
    newrelic.agent.initialize("newrelic.ini", environment=environment)


# explicitly set thread number for each worker
# because default asyncio because will spawn excess threads
# https://bugs.python.org/issue35279
max_threads_per_worker = 1
multiprocessing.set_start_method("spawn", True)
executor = None


# http://docs.gunicorn.org/en/stable/settings.html#post-worker-init
def post_worker_init(worker):
    """
    After worker is initialized, set up thread pool executor so we do not create idle threads when executor is invoked
    https://github.com/python/cpython/blob/e09359112e250268eca209355abeb17abf822486/Lib/concurrent/futures/thread.py#L181

    This can cause system mem starvation: https://bugs.python.org/issue35279

    :param worker:
    :return:
    """
    global executor

    import asyncio
    from uvicorn.loops.auto import auto_loop_setup

    auto_loop_setup()

    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=max_threads_per_worker)
    loop.set_default_executor(executor)


# http://docs.gunicorn.org/en/stable/settings.html#worker-exit
def worker_exit(server, worker):
    global executor
    if executor is not None:
        executor.shutdown(wait=False)
