import os


loglevel = "info"
workers = 2
bind = "0.0.0.0:80"
keepalive = 120
errorlog = "-"
proc_name = "payment-service"
max_requests = 5000
max_requests_jitter = 500


def post_fork(server, worker):
    import newrelic.agent
    import newrelic.core

    from app.commons.config.newrelic import create_new_relic_config

    from app.commons.instrumentation.newrelic_monkeypatch import monkeypatch_for_asyncio

    # monkeypatch newrelic for asyncio to preserve the root transaction
    monkeypatch_for_asyncio()

    environment = os.environ.get("ENVIRONMENT", "unknown")

    # new relic config
    config = create_new_relic_config(environment)
    settings = newrelic.agent.global_settings()

    # set the license key for the newrelic agent
    settings.license_key = config.NEW_RELIC_LICENSE_KEY.value

    # and then initialize
    newrelic.agent.initialize("newrelic.ini", environment=environment)
