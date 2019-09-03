from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from pydantic import Json

from sqlalchemy import ARRAY, Column, DateTime, Integer, Text, text
from typing_extensions import final

from app.commons.database.model import DBEntity, TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PayoutTable(TableDefinition):
    name: str = no_init_field("payouts")
    id: Column = no_init_field(
        Column(
            "id",
            Integer,
            primary_key=True,
            server_default=text("nextval('payouts_id_seq'::regclass)"),
        )
    )
    amount: Column = no_init_field(Column("amount", Integer, nullable=False))
    payment_account_id: Column = no_init_field(
        Column("payment_account_id", Integer, nullable=False)
    )
    status: Column = no_init_field(Column("status", Text, nullable=False))
    currency: Column = no_init_field(Column("currency", Text, nullable=False))
    fee: Column = no_init_field(Column("fee", Integer, nullable=False))
    type: Column = no_init_field(Column("type", Text, nullable=False))
    created_at: Column = no_init_field(
        Column("created_at", DateTime(True), nullable=False)
    )
    updated_at: Column = no_init_field(
        Column("updated_at", DateTime(True), nullable=False, onupdate=datetime.utcnow)
    )
    idempotency_key: Column = no_init_field(
        Column("idempotency_key", Text, nullable=False)
    )
    payout_method_id: Column = no_init_field(
        Column("payout_method_id", Integer, nullable=False)
    )
    transaction_ids: Column = no_init_field(
        Column("transaction_ids", ARRAY(Integer), nullable=False)
    )
    token: Column = no_init_field(Column("token", Text, nullable=False))
    fee_transaction_id: Column = no_init_field(Column("fee_transaction_id", Integer))
    error: Column = no_init_field(Column("error", Text))  # json string


class _PayoutPartial(DBEntity):
    amount: Optional[int]
    payment_account_id: Optional[int]
    status: Optional[str]
    currency: Optional[str]
    fee: Optional[int]
    type: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    idempotency_key: Optional[str]
    payout_method_id: Optional[int]
    transaction_ids: Optional[List[int]]
    token: Optional[str]
    fee_transaction_id: Optional[int]
    error: Optional[Json]

    def _fields_need_json_to_string_conversion(self):
        return ["error"]


class Payout(_PayoutPartial):
    id: int
    amount: int
    payment_account_id: int
    status: str
    currency: str
    fee: int
    type: str
    created_at: datetime
    updated_at: datetime
    idempotency_key: str
    payout_method_id: int
    transaction_ids: List[int]
    token: str


class PayoutCreate(_PayoutPartial):
    pass


class PayoutUpdate(_PayoutPartial):
    pass
