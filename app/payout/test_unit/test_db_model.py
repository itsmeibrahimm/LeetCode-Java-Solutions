from typing import Type

import pytest

from app.commons.database.model import DBEntity, TableDefinition
from app.payout.repository.maindb.model import PaymentAccountTable
from app.payout.repository.maindb.model.payment_account import (
    PaymentAccount,
    PaymentAccountUpdate,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
    StripeManagedAccountTable,
    StripeManagedAccount,
    StripeManagedAccountUpdate,
)
from app.payout.repository.maindb.model.stripe_transfer import (
    StripeTransfer,
    StripeTransferTable,
    StripeTransfer,
    StripeTransferUpdate,
)
from app.payout.repository.maindb.model.transfer import (
    Transfer,
    TransferTable,
    Transfer,
    TransferUpdate,
)
from app.commons.test_unit.database.utils import validation_db_entity_and_table_schema

test_db_entity_and_table_definition_data = [
    (PaymentAccount, PaymentAccountTable),
    (PaymentAccountUpdate, PaymentAccountTable),
    (StripeManagedAccount, StripeManagedAccountTable),
    (StripeManagedAccount, StripeManagedAccountTable),
    (StripeManagedAccountUpdate, StripeManagedAccountTable),
    (Transfer, TransferTable),
    (Transfer, TransferTable),
    (TransferUpdate, TransferTable),
    (StripeTransfer, StripeTransferTable),
    (StripeTransfer, StripeTransferTable),
    (StripeTransferUpdate, StripeTransferTable),
]


@pytest.mark.parametrize(
    "db_entity_cls, table_definition_cls", test_db_entity_and_table_definition_data
)
def test_db_entity_and_table_definition(
    db_entity_cls: Type[DBEntity], table_definition_cls: Type[TableDefinition]
):
    validation_db_entity_and_table_schema(db_entity_cls, table_definition_cls)
