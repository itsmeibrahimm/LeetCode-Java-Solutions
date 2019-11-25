import os
import signal

# ensure that we load the logging configuration early
# so the logger is properly configured
from app.commons.context.logger import init_logger

_web_port = os.getenv("WEB_PORT", 8000)
bind = f"0.0.0.0:{_web_port}"
workers = 1
loglevel = "debug"
keepalive = 120
errorlog = "-"
proc_name = "payment-service"
reload = True


def post_fork(server, worker):
    init_logger.debug("gunicorn forked process", pid=worker.pid)


def worker_int(worker):
    """
    Use worker int hook to exist current worker process so
    latest application code change can be loaded by gunicorn when re-spawn
    """
    init_logger.info(f"worker (pid: {worker.pid}) existing")

    # send SIGTERM to running worker process to ensure resources are properly cleaned up
    os.kill(worker.pid, signal.SIGTERM)
