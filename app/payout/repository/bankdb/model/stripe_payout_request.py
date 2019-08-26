from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import Json

from sqlalchemy import Column, DateTime, Integer, JSON, Text, text, ForeignKey
from typing_extensions import final

from app.commons.database.model import DBEntity, TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


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
    response: Column = no_init_field(Column("response", JSON))
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
    request: Column = no_init_field(Column("request", JSON))
    status: Column = no_init_field(Column("status", Text, nullable=False))
    events: Column = no_init_field(Column("events", JSON))
    stripe_account_id: Column = no_init_field(
        Column("stripe_account_id", Text, nullable=True)
    )


class _StripePayoutRequestPartial(DBEntity):
    payout_id: Optional[int]
    idempotency_key: Optional[str]
    payout_method_id: Optional[int]
    response: Optional[Json]
    created_at: Optional[datetime]
    received_at: Optional[datetime]
    updated_at: Optional[datetime]
    stripe_payout_id: Optional[str]
    request: Optional[Json]
    status: Optional[str]
    events: Optional[Json[List[Dict]]]  # type: ignore
    stripe_account_id: Optional[str]


class StripePayoutRequest(_StripePayoutRequestPartial):
    id: int
    payout_id: int
    idempotency_key: str
    payout_method_id: int
    created_at: datetime
    updated_at: datetime
    status: str


class StripePayoutRequestCreate(_StripePayoutRequestPartial):
    pass


class StripePayoutRequestUpdate(_StripePayoutRequestPartial):
    pass
