from dataclasses import dataclass

from app.commons.context.app_context import AppContext
from app.commons.database.model import Database


@dataclass
class PayoutMainDBRepository:
    """
    Base repository containing Payout_MainDB connection resources
    """

    database: Database

    @classmethod
    def from_context(cls, context: AppContext):
        return cls(database=context.payout_maindb)
