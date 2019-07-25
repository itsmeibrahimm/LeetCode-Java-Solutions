from typing_extensions import Protocol

from app.commons.config.app_config import Secret


class PayinAppConfig(Protocol):
    PAYIN_MAINDB_URL: Secret
