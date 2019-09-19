# ensure that we load the logging configuration early
# so the logger is properly configured
from app.commons.context.logger import init_logger

loglevel = "info"
workers = 2
bind = "0.0.0.0:80"
keepalive = 120
errorlog = "-"
proc_name = "payment-service"
max_requests = 5000
max_requests_jitter = 500


def post_fork(server, worker):
    import os

    # ensure logger is loaded before newrelic init,
    # so we don't reload the module and get duplicate log messages
    init_logger.debug("gunicorn forked process", pid=os.getpid())

    from app.commons.config.newrelic_loader import init_newrelic_agent

    init_newrelic_agent()
