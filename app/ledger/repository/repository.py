from dataclasses import dataclass

from app.commons.database.model import Database
from app.commons.utils.dataclass_extensions import no_init_field
from app.ledger.repository.paymentdb.mx_transaction_repository import (
    MxTransactionRepository,
)


@dataclass
class LedgerRepositories:
    _maindb: Database
    _paymentdb: Database

    mx_transaction_repo: MxTransactionRepository = no_init_field()

    def __post_init__(self):
        # payment db
        self.mx_transaction_repo = MxTransactionRepository(self._paymentdb)
