from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.sql.schema import SchemaItem
from typing_extensions import final

from app.commons.database.model import DBEntity, TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class TransferTable(TableDefinition):
    name: str = no_init_field("transfer")
    id: Column = no_init_field(
        Column(
            "id",
            Integer,
            primary_key=True,
            server_default=text("nextval('transfer_id_seq'::regclass)"),
        )
    )
    recipient_id: Column = no_init_field(Column("recipient_id", Integer))
    subtotal: Column = no_init_field(Column("subtotal", Integer, nullable=False))
    adjustments: Column = no_init_field(Column("adjustments", Text, nullable=False))
    amount: Column = no_init_field(Column("amount", Integer, nullable=False))
    currency: Column = no_init_field(Column("currency", Text))
    created_at: Column = no_init_field(
        Column(
            "created_at", DateTime(True), nullable=False, default=datetime.utcnow
        )  # come back and revisit this timeout to be consistent with DSJ
    )
    submitted_at: Column = no_init_field(Column("submitted_at", DateTime(True)))
    deleted_at: Column = no_init_field(Column("deleted_at", DateTime(True)))
    method: Column = no_init_field(Column("method", String(15), nullable=False))
    manual_transfer_reason: Column = no_init_field(
        Column("manual_transfer_reason", Text)
    )
    status: Column = no_init_field(Column("status", Text, index=True))
    status_code: Column = no_init_field(Column("status_code", Text))
    submitting_at: Column = no_init_field(Column("submitting_at", DateTime(True)))
    should_retry_on_failure: Column = no_init_field(
        Column("should_retry_on_failure", Boolean)
    )
    statement_description: Column = no_init_field(Column("statement_description", Text))
    created_by_id: Column = no_init_field(Column("created_by_id", Integer))
    deleted_by_id: Column = no_init_field(Column("deleted_by_id", Integer))
    payment_account_id: Column = no_init_field(
        Column("payment_account_id", Integer, index=True)
    )
    recipient_ct_id: Column = no_init_field(
        Column(
            "recipient_ct_id",
            Integer,
            ForeignKey("django_content_type.id", deferrable=True, initially="DEFERRED"),
            index=True,
        )
    )
    submitted_by_id: Column = no_init_field(Column("submitted_by_id", Integer))
    additional_schema_args: List[SchemaItem] = no_init_field(
        [CheckConstraint("recipient_id >= 0")]
    )


class Transfer(DBEntity):
    id: Optional[int]  # server default generated
    created_at: Optional[datetime]  # client table definition default generated

    subtotal: int
    adjustments: str
    amount: int
    method: str

    currency: Optional[str]
    submitted_at: Optional[datetime]
    deleted_at: Optional[datetime]
    manual_transfer_reason: Optional[str]
    status: Optional[str]
    status_code: Optional[str]
    submitting_at: Optional[datetime]
    should_retry_on_failure: Optional[bool]
    statement_description: Optional[str]
    created_by_id: Optional[int]
    deleted_by_id: Optional[int]
    payment_account_id: Optional[int]
    recipient_id: Optional[int]
    recipient_ct_id: Optional[int]
    submitted_by_id: Optional[int]


class TransferUpdate(DBEntity):
    subtotal: Optional[int]
    adjustments: Optional[str]
    amount: Optional[int]
    method: Optional[str]
    currency: Optional[str]
    submitted_at: Optional[datetime]
    deleted_at: Optional[datetime]
    manual_transfer_reason: Optional[str]
    status: Optional[str]
    status_code: Optional[str]
    submitting_at: Optional[datetime]
    should_retry_on_failure: Optional[bool]
    statement_description: Optional[str]
    created_by_id: Optional[int]
    deleted_by_id: Optional[int]
    payment_account_id: Optional[int]
    submitted_by_id: Optional[int]
