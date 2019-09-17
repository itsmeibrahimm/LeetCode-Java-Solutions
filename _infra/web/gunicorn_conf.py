loglevel = "info"
workers = 2
bind = "0.0.0.0:80"
keepalive = 120
errorlog = "-"
proc_name = "payment-service"
max_requests = 5000
max_requests_jitter = 500


def post_fork(server, worker):
    from app.commons.config.newrelic_loader import init_newrelic_agent

    init_newrelic_agent()
