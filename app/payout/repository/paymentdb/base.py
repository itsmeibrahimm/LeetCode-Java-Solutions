from abc import ABC

from app.commons.database.infra import DB


class PayoutPaymentDBRepository(ABC):
    """
    Base repository containing Payout_PaymentDB connection resources
    """

    _database: DB

    def __init__(self, *, _database: DB):
        self._database = _database
