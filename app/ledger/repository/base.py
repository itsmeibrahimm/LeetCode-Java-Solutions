from abc import ABC

from app.commons.database.infra import DB


class LedgerPaymentDBRepository(ABC):
    """
    Base repository containing Ledger_paymentdb connection resources
    """

    _database: DB

    def __init__(self, *, _database: DB):
        self._database = _database
