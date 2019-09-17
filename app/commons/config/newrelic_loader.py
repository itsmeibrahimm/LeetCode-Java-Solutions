def init_newrelic_agent():
    import os
    import sys

    import newrelic.agent
    import newrelic.core

    from app.commons.instrumentation.newrelic_monkeypatch import monkeypatch_for_asyncio

    # monkeypatch newrelic for asyncio to preserve the root transaction
    monkeypatch_for_asyncio()

    # keep track of modules loaded prior to ninox init (will unload)
    loaded_modules = set(sys.modules.keys())

    # get newrelic secrets from ninox
    from app.commons.config.newrelic import create_new_relic_config

    environment = os.environ.get("ENVIRONMENT", "unknown")

    # new relic config
    config = create_new_relic_config(environment)
    settings = newrelic.agent.global_settings()

    # set the license key for the newrelic agent
    settings.license_key = config.NEW_RELIC_LICENSE_KEY.value

    # unload imported modules - get rid of uninstrumeted warning from newrelic
    extra_modules = set(sys.modules.keys()) - loaded_modules
    for module in extra_modules:
        del sys.modules[module]
    del create_new_relic_config

    # and then initialize
    newrelic.agent.initialize("newrelic.ini", environment=environment)
