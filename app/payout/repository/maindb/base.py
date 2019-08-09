from abc import ABC

from app.commons.database.model import Database


class PayoutMainDBRepository(ABC):
    """
    Base repository containing Payout_MainDB connection resources
    """

    _database: Database

    def __init__(self, *, _database: Database):
        self._database = _database
