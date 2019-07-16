from typing import Union

import attr
from ninox.interface.flask.secret_marker import NinoxMarker


@attr.s(frozen=True, kw_only=True, auto_attribs=True)
class _Config:
    """
    A config class contains all necessary config key-values to bootstrap application.
    For local/staging/prod application environments, there are corresponding instances
    of this _Config class:
    - local: local.py::LOCAL
    - staging: staging.py::STAGING
    - prod: prod.py::PROD
    """

    DEBUG: bool
    NINOX_ENABLED: bool

    # Secret configurations start here
    TEST_SECRET: Union[str, NinoxMarker]
