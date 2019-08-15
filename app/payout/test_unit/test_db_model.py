from typing import Type

import pytest

from app.commons.database.model import DBEntity, TableDefinition
from app.commons.test_unit.database.utils import validation_db_entity_and_table_schema
from app.payout.repository.maindb.model import PaymentAccountTable
from app.payout.repository.maindb.model.payment_account import (
    PaymentAccountEntity,
    # PaymentAccountCreate,
    PaymentAccountUpdate,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountEntity,
    StripeManagedAccountTable,
    # StripeManagedAccountCreate,
    StripeManagedAccountUpdate,
)
from app.payout.repository.maindb.model.stripe_transfer import (
    StripeTransferEntity,
    StripeTransferTable,
    # StripeTransferCreate,
    StripeTransferUpdate,
)
from app.payout.repository.maindb.model.transfer import (
    TransferEntity,
    TransferTable,
    # TransferCreate,
    TransferUpdate,
)

# from app.payout.repository.bankdb.model.payout import Payout, PayoutTable, PayoutCreate
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestEntity,
    # StripePayoutRequestCreate,
    StripePayoutRequestTable,
)

test_db_entity_and_table_definition_data = [
    (PaymentAccountEntity, PaymentAccountTable),
    # (PaymentAccountCreate, PaymentAccountTable),
    (PaymentAccountUpdate, PaymentAccountTable),
    (StripeManagedAccountEntity, StripeManagedAccountTable),
    # (StripeManagedAccountCreate, StripeManagedAccountTable),
    (StripeManagedAccountUpdate, StripeManagedAccountTable),
    (TransferEntity, TransferTable),
    # (TransferCreate, TransferTable),
    (TransferUpdate, TransferTable),
    (StripeTransferEntity, StripeTransferTable),
    # (StripeTransferCreate, StripeTransferTable),
    (StripeTransferUpdate, StripeTransferTable),
    # (Payout, PayoutTable),
    # (PayoutCreate, PayoutTable),
    (StripePayoutRequestEntity, StripePayoutRequestTable),
    # (StripePayoutRequestCreate, StripePayoutRequestTable),
]


@pytest.mark.parametrize(
    "db_entity_cls, table_definition_cls", test_db_entity_and_table_definition_data
)
def test_db_entity_and_table_definition(
    db_entity_cls: Type[DBEntity], table_definition_cls: Type[TableDefinition]
):
    validation_db_entity_and_table_schema(db_entity_cls, table_definition_cls)
