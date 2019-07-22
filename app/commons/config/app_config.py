from __future__ import annotations

import attr
from typing_extensions import final


@final
@attr.s(frozen=True, auto_attribs=True)
class AppConfig:
    """
    A config class contains all necessary config key-values to bootstrap application.
    For local/staging/prod application environments, there are corresponding instances
    of this _Config class:
    - local: local.py::LOCAL
    - staging: staging.py::STAGING
    - prod: prod.py::PROD
    TODO: breakdown this to decouple paying/payout subapp configs
    """

    DEBUG: bool
    NINOX_ENABLED: bool

    # Secret configurations start here
    # These ought to be Ninox marker or a proper secret type, will be updated once Ninox fastAPI integration is in place
    TEST_SECRET: str
    PAYOUT_MAINDB_URL: str
    PAYOUT_BANKDB_URL: str
    PAYIN_MAINDB_URL: str
