from abc import ABC

from app.commons.database.infra import DB


class NonValidReplicaOperation(Exception):
    pass


class PurchaseCardMainDBRepository(ABC):
    """
    Base repository containing PurchaseCard_MainDB connection resources
    """

    _database: DB

    def __init__(self, *, _database: DB):
        self._database = _database


class PurchaseCardPaymentDBRepository(ABC):
    """
    Base repository containing PurchaseCard_PaymentDB connection resources
    """

    _database: DB

    def __init__(self, *, _database: DB):
        self._database = _database
