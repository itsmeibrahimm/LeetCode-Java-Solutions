from dataclasses import InitVar, dataclass

from app.commons.context.app_context import AppContext
from app.commons.database.model import Database
from app.commons.utils.dataclass_extensions import no_init_field


@dataclass
class PayinDBRepository:
    """
    Base repository containing Payin_PaymentDB connection resources
    """

    context: InitVar[AppContext]  # constructor use only, not persisted in repo instance
    main_database: Database = no_init_field()
    payment_database: Database = no_init_field()

    def __post_init__(self, context: AppContext):
        self.main_database = context.payin_maindb
        self.payment_database = context.payin_paymentdb
