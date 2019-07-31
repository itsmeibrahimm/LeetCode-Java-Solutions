from dataclasses import InitVar, dataclass

from app.commons.database.model import Database, DBContext
from app.commons.utils.dataclass_extensions import no_init_field


@dataclass
class PayoutMainDBRepository:
    """
    Base repository containing Payout_MainDB connection resources
    """

    db_context: InitVar[
        DBContext
    ]  # constructor use only, not persisted in repo instance
    database: Database = no_init_field()

    def __post_init__(self, db_context: DBContext):
        self.database = db_context.payout_maindb
