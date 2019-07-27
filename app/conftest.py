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
async def payin_maindb(app_config: AppConfig) -> Gino:
    """
    initialize the maindb connection for PayIn user
    """
    db = await Gino(app_config.PAYIN_MAINDB_URL.value)
    yield db
    await db.pop_bind().close()


@pytest.fixture
async def payout_maindb(app_config: AppConfig) -> Gino:
    """
    initialize the maindb connection for PayOut user
    """
    db = await Gino(app_config.PAYOUT_MAINDB_URL.value)
    yield db
    await db.pop_bind().close()


@pytest.fixture
async def payout_bankdb(app_config: AppConfig) -> Gino:
    """
    initialize the bankdb connection for PayOut user
    """
    db = await Gino(app_config.PAYOUT_BANKDB_URL.value)
    yield db
    await db.pop_bind().close()
