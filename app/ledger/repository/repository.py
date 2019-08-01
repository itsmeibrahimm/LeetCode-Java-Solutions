from dataclasses import dataclass

from gino import Gino

from app.commons.utils.dataclass_extensions import no_init_field
from app.ledger.repository.paymentdb.mx_transaction_repository import (
    MxTransactionRepository,
)


@dataclass
class LedgerRepositories:
    _maindb_connection: Gino
    _paymentdb_connection: Gino

    mx_transaction_repo: MxTransactionRepository = no_init_field()

    def __post_init__(self):
        # payment db
        self.mx_transaction_repo = MxTransactionRepository(self._paymentdb_connection)
