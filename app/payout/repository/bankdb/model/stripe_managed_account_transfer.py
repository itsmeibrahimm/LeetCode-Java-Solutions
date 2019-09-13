from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, Text, text
from typing_extensions import final

from app.commons.database.model import DBEntity, TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class StripeManagedAccountTransferTable(TableDefinition):
    name: str = no_init_field("transfers")
    id: Column = no_init_field(
        Column(
            "id",
            Integer,
            primary_key=True,
            server_default=text(
                "nextval('stripe_managed_account_transfers_id_seq'::regclass)"
            ),
        )
    )
    amount: Column = no_init_field(Column("amount", Integer, nullable=False))
    from_stripe_account_id: Column = no_init_field(
        Column("from_stripe_account_id", Text, nullable=False)
    )
    to_stripe_account_id: Column = no_init_field(
        Column("to_stripe_account_id", Text, nullable=False)
    )
    token: Column = no_init_field(Column("token", Text, nullable=False))
    fee: Column = no_init_field(Column("fee", Integer, nullable=True))
    created_at: Column = no_init_field(
        Column("created_at", DateTime(True), nullable=False)
    )
    updated_at: Column = no_init_field(
        Column("updated_at", DateTime(True), nullable=False)
    )


class _StripeManagedAccountTransferPatial(DBEntity):
    amount: Optional[int]
    from_stripe_account_id: Optional[str]
    to_stripe_account_id: Optional[str]
    token: Optional[str]
    fee: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class StripeManagedAccountTransfer(_StripeManagedAccountTransferPatial):
    id: int
    created_at: datetime
    updated_at: datetime

    amount: int
    from_stripe_account_id: str
    to_stripe_account_id: str
    token: str


class StripeManagedAccountTransferCreate(_StripeManagedAccountTransferPatial):
    amount: int
    from_stripe_account_id: str
    to_stripe_account_id: str
    token: str


class StripeManagedAccountTransferUpdate(_StripeManagedAccountTransferPatial):
    pass
