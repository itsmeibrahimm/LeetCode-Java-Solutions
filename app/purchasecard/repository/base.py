from abc import ABC

from app.commons.database.infra import DB


class PurchaseCardMainDBRepository(ABC):
    """
    Base repository containing PurchaseCard_MainDB connection resources
    """

    _database: DB

    def __init__(self, *, _database: DB):
        self._database = _database
