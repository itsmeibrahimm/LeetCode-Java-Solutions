from dataclasses import InitVar, dataclass
from starlette.requests import Request

from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.database.client.interface import EngineTransactionContext
from app.commons.database.infra import DB
from app.commons.utils.dataclass_extensions import no_init_field


@dataclass
class PayinDBRepository:
    """
    Base repository containing Payin_PaymentDB connection resources
    """

    context: InitVar[AppContext]  # constructor use only, not persisted in repo instance
    main_database: DB = no_init_field()
    payment_database: DB = no_init_field()

    def __post_init__(self, context: AppContext):
        self.main_database = context.payin_maindb
        self.payment_database = context.payin_paymentdb

    def main_database_transaction(self) -> EngineTransactionContext:
        return self.main_database.master().transaction()

    def payment_database_transaction(self) -> EngineTransactionContext:
        return self.payment_database.master().transaction()

    @classmethod
    def get_repository(cls, request: Request):
        app_context: AppContext = get_global_app_context(request)
        return cls(context=app_context)
