from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, text
from typing_extensions import final

from app.commons.database.model import DBEntity, TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class StripeTransferTable(TableDefinition):
    name: str = no_init_field("stripe_transfer")
    id: Column = no_init_field(
        Column(
            "id",
            Integer,
            primary_key=True,
            server_default=text("nextval('stripe_transfer_id_seq'::regclass)"),
        )
    )
    created_at: Column = no_init_field(
        Column(
            "created_at", DateTime(True), nullable=False, default=datetime.now
        )  # come back and revisit this timeout to be consistent with DSJ
    )
    stripe_id: Column = no_init_field(Column("stripe_id", String(50), index=True))
    stripe_request_id: Column = no_init_field(Column("stripe_request_id", Text))
    stripe_status: Column = no_init_field(
        Column("stripe_status", String(10), nullable=False)
    )
    stripe_failure_code: Column = no_init_field(
        Column("stripe_failure_code", String(50))
    )
    stripe_account_id: Column = no_init_field(Column("stripe_account_id", Text))
    stripe_account_type: Column = no_init_field(Column("stripe_account_type", Text))
    country_shortname: Column = no_init_field(Column("country_shortname", Text))
    bank_last_four: Column = no_init_field(Column("bank_last_four", Text))
    bank_name: Column = no_init_field(Column("bank_name", Text))
    transfer_id: Column = no_init_field(
        Column(
            "transfer_id",
            Integer,
            ForeignKey("transfer.id", deferrable=True, initially="DEFERRED"),
            nullable=False,
            index=True,
        )
    )
    submission_error_code: Column = no_init_field(Column("submission_error_code", Text))
    submission_error_type: Column = no_init_field(Column("submission_error_type", Text))
    submission_status: Column = no_init_field(Column("submission_status", Text))
    submitted_at: Column = no_init_field(Column("submitted_at", DateTime(True)))


class StripeTransfer(DBEntity):
    id: Optional[int]
    transfer_id: int
    stripe_status: str
    created_at: Optional[datetime]
    stripe_id: Optional[str]
    stripe_request_id: Optional[str]
    stripe_failure_code: Optional[str]
    stripe_account_id: Optional[str]
    stripe_account_type: Optional[str]
    country_shortname: Optional[str]
    bank_last_four: Optional[str]
    bank_name: Optional[str]
    submission_error_code: Optional[str]
    submission_error_type: Optional[str]
    submission_status: Optional[str]
    submitted_at: Optional[datetime]


class StripeTransferWrite(StripeTransfer):
    pass


class StripeTransferUpdate(DBEntity):
    stripe_status: Optional[str]
    transfer_id: Optional[int]
    stripe_id: Optional[str]
    stripe_request_id: Optional[str]
    stripe_failure_code: Optional[str]
    stripe_account_id: Optional[str]
    stripe_account_type: Optional[str]
    country_shortname: Optional[str]
    bank_last_four: Optional[str]
    bank_name: Optional[str]
    submission_error_code: Optional[str]
    submission_error_type: Optional[str]
    submission_status: Optional[str]
    submitted_at: Optional[datetime]
