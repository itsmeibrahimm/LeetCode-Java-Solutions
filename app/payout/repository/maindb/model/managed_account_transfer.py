from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    Text,
    text,
    String,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.sql.schema import SchemaItem
from typing_extensions import final

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class ManagedAccountTransferTable(TableDefinition):
    name: str = no_init_field("managed_account_transfer")
    id: Column = no_init_field(
        Column(
            "id",
            Integer,
            primary_key=True,
            server_default=text("nextval('managed_account_transfer_id_seq'::regclass)"),
        )
    )
    account_id: Column = no_init_field(Column("account_id", Integer))
    amount: Column = no_init_field(Column("amount", Integer, nullable=False))
    currency: Column = no_init_field(Column("currency", Text))
    stripe_id: Column = no_init_field(Column("stripe_id", String(50), nullable=False))
    stripe_status: Column = no_init_field(
        Column("stripe_status", String(10), nullable=False)
    )
    created_at: Column = no_init_field(
        Column("created_at", DateTime(True), nullable=False)
    )
    submitted_at: Column = no_init_field(Column("submitted_at", DateTime(True)))
    account_ct_id: Column = no_init_field(
        Column(
            "account_ct_id",
            ForeignKey("django_content_type.id", deferrable=True, initially="DEFERRED"),
            index=True,
        )
    )
    payment_account_id: Column = no_init_field(
        Column("payment_account_id", Integer, index=True)
    )
    transfer_id: Column = no_init_field(
        Column(
            "transfer_id",
            ForeignKey("transfer.id", deferrable=True, initially="DEFERRED"),
            nullable=False,
            unique=True,
        )
    )
    additional_schema_args: List[SchemaItem] = no_init_field(
        [CheckConstraint("account_id >= 0")]
    )


# Partial is the overlap of ManagedAccountTransfer, create and update
# Everything inside should be optional regardless of its db definition
# Anything that should not be optional will be overwritten
class _ManagedAccountTransferPartial(DBEntity):
    amount: Optional[int]
    transfer_id: Optional[int]
    stripe_id: Optional[str]
    stripe_status: Optional[str]
    created_at: Optional[datetime]
    submitted_at: Optional[datetime]
    payment_account_id: Optional[int]
    account_ct_id: Optional[int]
    account_id: Optional[int]
    currency: Optional[str]


class ManagedAccountTransfer(_ManagedAccountTransferPartial):
    id: int  # server default generated
    created_at: datetime

    amount: int
    transfer_id: int
    stripe_id: str
    stripe_status: str
    currency: str


class ManagedAccountTransferCreate(_ManagedAccountTransferPartial):
    amount: int
    transfer_id: int

    payment_account_id: int


class ManagedAccountTransferUpdate(_ManagedAccountTransferPartial):
    pass
