from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, Text, text, ForeignKey, JSON
from typing_extensions import final

from app.commons.database.model import DBEntity, TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field
from ..types import BankDBBrokenJson


@final
@dataclass(frozen=True)
class StripePayoutRequestTable(TableDefinition):
    name: str = no_init_field("stripe_payout_requests")
    id: Column = no_init_field(
        Column(
            "id",
            Integer,
            primary_key=True,
            server_default=text("nextval('stripe_payout_requests_id_seq'::regclass)"),
        )
    )
    payout_id: Column = no_init_field(
        Column(
            "payout_id",
            Integer,
            ForeignKey("payout.id", deferrable=True, initially="DEFERRED"),
            nullable=False,
            unique=True,
        )
    )
    idempotency_key: Column = no_init_field(
        Column("idempotency_key", Text, nullable=False)
    )
    payout_method_id: Column = no_init_field(
        Column("payout_method_id", Integer, nullable=False)
    )
    response: Column = no_init_field(Column("response", JSON))  # json string
    created_at: Column = no_init_field(
        Column("created_at", DateTime(True), nullable=False)
    )
    received_at: Column = no_init_field(
        Column("received_at", DateTime(True), nullable=True)
    )
    updated_at: Column = no_init_field(
        Column("updated_at", DateTime(True), nullable=False, onupdate=datetime.utcnow)
    )
    stripe_payout_id: Column = no_init_field(
        Column("stripe_payout_id", Text, nullable=True)
    )
    request: Column = no_init_field(Column("request", JSON))  # json string
    status: Column = no_init_field(Column("status", Text, nullable=False))
    events: Column = no_init_field(Column("events", JSON))  # json string
    stripe_account_id: Column = no_init_field(
        Column("stripe_account_id", Text, nullable=True)
    )


class _StripePayoutRequestPartial(DBEntity):
    payout_id: Optional[int]
    idempotency_key: Optional[str]
    payout_method_id: Optional[int]
    response: Optional[BankDBBrokenJson]
    created_at: Optional[datetime]
    received_at: Optional[datetime]
    updated_at: Optional[datetime]
    stripe_payout_id: Optional[str]
    request: Optional[BankDBBrokenJson]
    status: Optional[str]
    events: Optional[BankDBBrokenJson]
    stripe_account_id: Optional[str]

    def _fields_need_json_to_string_conversion(self):
        # this field is saved as string even though it defined as json in DB
        # https://github.com/doordash/bank-service/blob/99de03d82e132d599057bb5a8218eb661976418f/bankservice/adapters/database/repositories/stripe_payout_requests/stripe_payout_request_repository.py#L32
        # keep the same behavior until we fix them all
        return ["request"]


class StripePayoutRequest(_StripePayoutRequestPartial):
    id: int
    payout_id: int
    idempotency_key: str
    payout_method_id: int
    created_at: datetime
    updated_at: datetime
    status: str


class StripePayoutRequestCreate(_StripePayoutRequestPartial):
    # based on the usage in DSJ
    payout_id: int
    idempotency_key: str
    payout_method_id: int
    stripe_account_id: str
    status: str


class StripePayoutRequestUpdate(_StripePayoutRequestPartial):
    pass
