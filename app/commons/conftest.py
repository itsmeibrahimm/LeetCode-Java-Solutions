import os
from typing import Dict, List, Tuple, Union

import pytest

from app.commons.context.logger import get_logger
from app.commons.database.infra import DB
from app.payout.repository.paymentdb.payout_lock import PayoutLockRepository

os.environ["ENVIRONMENT"] = "testing"

stats_logger = get_logger("statsd")

RuntimeTypes = Union[Dict, List, Tuple, bool, str, int, float]

#####################
# DB Fixtures
#####################
@pytest.fixture
def payout_lock_repo(payout_paymentdb: DB) -> PayoutLockRepository:
    return PayoutLockRepository(database=payout_paymentdb)
