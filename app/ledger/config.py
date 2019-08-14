from typing_extensions import Protocol

from app.commons.config.secrets import Secret


class PayinAppConfig(Protocol):
    PAYIN_MAINDB_URL: Secret
