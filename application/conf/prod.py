from ninox.interface.flask.secret_marker import NinoxMarker

from .config import _Config

"""
Production configurations which will be loaded to Flask App.config dictionary at when application is created.
This should also serve as base configuration to be extended by local or staging environment to make sure local or
staging environment always intentionally pick up same set of configuration keys as Prod.
"""
PROD = _Config(
    DEBUG=False,
    NINOX_ENABLED=True,
    # Secret configurations start here
    TEST_SECRET=NinoxMarker(),
)
