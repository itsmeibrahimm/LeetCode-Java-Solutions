from dataclasses import InitVar, dataclass

from app.commons.context.app_context import AppContext
from app.commons.database.infra import DB
from app.commons.utils.dataclass_extensions import no_init_field


@dataclass
class LedgerDBRepository:
    """
    Base repository containing Ledger_PaymentDB connection resources
    """

    context: InitVar[AppContext]  # constructor use only, not persisted in repo instance
    main_database: DB = no_init_field()
    payment_database: DB = no_init_field()

    def __post_init__(self, context: AppContext):
        self.main_database = context.ledger_maindb
        self.payment_database = context.ledger_paymentdb
