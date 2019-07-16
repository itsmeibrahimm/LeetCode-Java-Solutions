from ninox.interface.flask.secret_marker import NinoxMarker

from .config import _Config

"""
Configurations loaded to Flask App.config dictionary when ENVIRONMENT=staging
"""
STAGING = _Config(
    DEBUG=False,
    NINOX_ENABLED=True,
    # Secret configurations start here
    TEST_SECRET=NinoxMarker(),
)
