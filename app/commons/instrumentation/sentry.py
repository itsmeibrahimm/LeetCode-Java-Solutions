import sentry_sdk

from app.commons.config.app_config import SentryConfig
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration


def init_sentry_sdk(sentry_config: SentryConfig):
    sentry_sdk.init(
        dsn=sentry_config.dsn.value,
        environment=sentry_config.environment,
        release=sentry_config.release,
        integrations=[AioHttpIntegration(), SqlalchemyIntegration()],
        # also include default integrations
        # https://docs.sentry.io/platforms/python/default-integrations/
        default_integrations=True,
    )
