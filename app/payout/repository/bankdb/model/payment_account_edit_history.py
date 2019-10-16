from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, Text, text, TIMESTAMP
from typing_extensions import final

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PaymentAccountEditHistoryTable(TableDefinition):
    name: str = no_init_field("payment_account_edit_history")
    id: Column = no_init_field(
        Column(
            "id",
            Integer,
            primary_key=True,
            server_default=text(
                "nextval('payment_account_edit_history_id_seq'::regclass)"
            ),
        )
    )
    timestamp: Column = no_init_field(
        Column("timestamp", TIMESTAMP(True), nullable=False)
    )
    user_id: Column = no_init_field(Column("user_id", Integer))
    device_id: Column = no_init_field(Column("device_id", Text))
    ip: Column = no_init_field(Column("ip", Text))
    payment_account_id: Column = no_init_field(Column("payment_account_id", Integer))
    owner_type: Column = no_init_field(Column("owner_type", Text))
    owner_id: Column = no_init_field(Column("owner_id", Integer))

    account_type: Column = no_init_field(Column("account_type", Text, nullable=False))
    account_id: Column = no_init_field(Column("account_id", Integer, nullable=False))

    old_bank_name: Column = no_init_field(Column("old_bank_name", Text))
    new_bank_name: Column = no_init_field(Column("new_bank_name", Text, nullable=False))
    old_bank_last4: Column = no_init_field(Column("old_bank_last4", Text))
    new_bank_last4: Column = no_init_field(
        Column("new_bank_last4", Text, nullable=False)
    )
    old_fingerprint: Column = no_init_field(Column("old_fingerprint", Text))
    new_fingerprint: Column = no_init_field(
        Column("new_fingerprint", Text, nullable=False)
    )
    login_as_user_id: Column = no_init_field(Column("login_as_user_id", Integer))
    notes: Column = no_init_field(Column("notes", Text))


class _PaymentAccountEditHistory(DBEntity):
    timestamp: Optional[datetime]
    account_type: Optional[str]
    account_id: Optional[int]
    new_bank_name: Optional[str]
    new_bank_last4: Optional[str]
    new_fingerprint: Optional[str]


class PaymentAccountEditHistory(_PaymentAccountEditHistory):
    id: int
    timestamp: datetime
    account_type: str
    account_id: int
    new_bank_name: str
    new_bank_last4: str
    new_fingerprint: str
