import os
import pytest
from gino import Gino
from app.commons.config.app_config import AppConfig

os.environ["ENVIRONMENT"] = "testing"


@pytest.fixture
def app_config():
    from app.commons.config.utils import init_app_config

    return init_app_config()


@pytest.fixture
async def payin_maindb(app_config: AppConfig):
    """
    initialize the maindb connection for PayIn user
    """
    return await Gino(app_config.PAYIN_MAINDB_URL.value)


@pytest.fixture
async def payout_maindb(app_config: AppConfig):
    """
    initialize the maindb connection for PayOut user
    """
    return await Gino(app_config.PAYOUT_MAINDB_URL.value)


@pytest.fixture
async def payout_bankdb(app_config: AppConfig):
    """
    initialize the bankdb connection for PayOut user
    """
    return await Gino(app_config.PAYOUT_BANKDB_URL.value)
