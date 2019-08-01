from dataclasses import InitVar, dataclass

from app.commons.context.app_context import AppContext
from app.commons.database.model import Database
from app.commons.utils.dataclass_extensions import no_init_field


@dataclass
class PayoutMainDBRepository:
    """
    Base repository containing Payout_MainDB connection resources
    """

    context: InitVar[AppContext]  # constructor use only, not persisted in repo instance
    database: Database = no_init_field()

    def __post_init__(self, context: AppContext):
        self.database = context.payout_maindb
