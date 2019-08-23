from typing import Type
import pytest

from app.commons.database.model import DBEntity, TableDefinition
from app.commons.test_unit.database.utils import validation_db_entity_and_table_schema
from app.ledger.core.mx_ledger.model import MxLedger

from app.ledger.core.mx_transaction.model import MxScheduledLedger, MxTransaction
from app.ledger.models.paymentdb import (
    MxLedgerTable,
    MxScheduledLedgerTable,
    MxTransactionTable,
)

test_db_entity_and_table_definition_data = [
    (MxLedger, MxLedgerTable),
    (MxScheduledLedger, MxScheduledLedgerTable),
    (MxTransaction, MxTransactionTable),
]


@pytest.mark.parametrize(
    "db_entity_cls, table_definition_cls", test_db_entity_and_table_definition_data
)
def test_db_entity_and_table_definition(
    db_entity_cls: Type[DBEntity], table_definition_cls: Type[TableDefinition]
):
    validation_db_entity_and_table_schema(db_entity_cls, table_definition_cls)
