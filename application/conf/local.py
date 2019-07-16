import os

from .config import _Config

"""
Configurations loaded to Flask App.config dictionary when ENVIRONMENT=local
"""
LOCAL = _Config(
    DEBUG=True,
    NINOX_ENABLED=False,
    # Secret configurations start here
    TEST_SECRET=os.getenv("TEST_SECRET", "local_test_secret"),
)
