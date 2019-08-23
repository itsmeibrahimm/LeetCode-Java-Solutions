from typing import Any

from app.ledger.core.mx_ledger.model import MxLedger
from app.ledger.core.mx_transaction.model import MxTransaction


def to_mx_ledger(row: Any) -> MxLedger:
    return MxLedger.from_orm(row)


def to_mx_transaction(row: Any) -> MxTransaction:
    return MxTransaction.from_orm(row)
