###########################################################
#     MxTransaction DBEntity and CRUD operations          #
###########################################################
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.commons.database.model import DBEntity, DBRequestModel
from app.commons.types import CurrencyType
from app.ledger.core.mx_transaction.types import (
    MxLedgerType,
    MxScheduledLedgerIntervalType,
    MxTransactionType,
)


class MxTransactionDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: UUID
    payment_account_id: str
    amount: int
    currency: str
    ledger_id: UUID
    idempotency_key: str
    target_type: str
    routing_key: datetime
    target_id: Optional[str]
    legacy_transaction_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    context: Optional[str]
    metadata: Optional[str]


class InsertMxTransactionInput(MxTransactionDbEntity):
    pass


class InsertMxTransactionOutput(MxTransactionDbEntity):
    pass


class InsertMxTransactionWithLedgerInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    currency: CurrencyType
    amount: int
    type: MxLedgerType
    payment_account_id: str
    interval_type: MxScheduledLedgerIntervalType
    routing_key: datetime
    idempotency_key: str
    target_type: MxTransactionType
    legacy_transaction_id: Optional[str]
    target_id: Optional[str]
    context: Optional[str]
    metadata: Optional[str]


###########################################################
#   MxScheduledLedger DBEntity and CRUD operations        #
###########################################################
class MxScheduledLedgerDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: UUID
    payment_account_id: str
    ledger_id: UUID
    interval_type: str
    start_time: datetime
    end_time: datetime
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class InsertMxScheduledLedgerInput(MxScheduledLedgerDbEntity):
    pass


class InsertMxScheduledLedgerOutput(MxScheduledLedgerDbEntity):
    pass


class GetMxScheduledLedgerByLedgerInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    id: UUID


class GetMxScheduledLedgerByLedgerOutput(MxScheduledLedgerDbEntity):
    pass


class GetMxScheduledLedgerInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    payment_account_id: str
    routing_key: datetime
    interval_type: MxScheduledLedgerIntervalType


class GetMxScheduledLedgerOutput(MxScheduledLedgerDbEntity):
    pass


###########################################################
#       MxLedger DBEntity and CRUD operations             #
###########################################################
class MxLedgerDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: UUID
    type: str
    currency: str
    state: str
    balance: int
    payment_account_id: str
    legacy_transfer_id: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    submitted_at: Optional[datetime]
    amount_paid: Optional[int]
    finalized_at: Optional[datetime]
    created_by_employee_id: Optional[str]
    submitted_by_employee_id: Optional[str]
    rolled_to_ledger_id: Optional[str]


class InsertMxLedgerInput(MxLedgerDbEntity):
    pass


class InsertMxLedgerOutput(MxLedgerDbEntity):
    pass


class UpdateMxLedgerSetInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    balance: int


class UpdateMxLedgerWhereInput(DBRequestModel):
    id: UUID


class UpdateMxLedgerOutput(MxLedgerDbEntity):
    pass


class GetMxLedgerByAccountInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    payment_account_id: str


class GetMxLedgerByAccountOutput(MxLedgerDbEntity):
    pass


class GetMxLedgerByIdInput(DBRequestModel):
    """
    The variable name must be consistent with DB table column name
    """

    id: UUID


class GetMxLedgerByIdOutput(MxLedgerDbEntity):
    pass
