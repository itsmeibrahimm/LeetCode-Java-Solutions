from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum

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
            "created_at", DateTime(True), nullable=False
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


class _TransferPartial(DBEntity):
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
    subtotal: Optional[int]
    adjustments: Optional[str]
    amount: Optional[int]
    method: Optional[str]


class Transfer(_TransferPartial):
    id: int
    created_at: datetime

    subtotal: int
    adjustments: str
    amount: int
    method: str


class TransferCreate(_TransferPartial):
    subtotal: int
    adjustments: str
    amount: int
    method: str


class TransferUpdate(_TransferPartial):
    pass


class TransferStatus(Enum):
    # The following comments are all guesses, based on reading through code -- @sean
    CREATING = (
        "creating"
    )  # When a Payout is created on DD, but also in the process of updating associated transactions
    CREATED = "created"  # When a Payout is created on stripe side
    NEW = (
        "new"
    )  # When a Payout has been created on DoorDash and ready for submission; Money is still in the Stripe Managed Account balance at this point
    SUBMITTING = (
        "submitting"
    )  # When a Payout has been created on DoorDash, and submission to Stripe is in progress
    PENDING = (
        "pending"
    )  # When a Payout is communicated to Stripe, but Stripe has yet to communicate to the Bank.  Money has left the Stripe Managed Account balance at this point
    IN_TRANSIT = (
        "in_transit"
    )  # When a Payout has been communicated to the Bank by Stripe
    PAID = (
        "paid"
    )  # When a Payout is confirmed to have depsited money into the managed account's Bank by Stripe
    FAILED = (
        "failed"
    )  # When a Payout is confirmed to have been failed by the Bank, Money has re-entered the Stripe Managed Account balance at this point
    CANCELLED = (
        "cancelled"
    )  # When a Payout is confirmed to have been cancelled (not sure by who), Money has re-entered the Stripe Managed Account balance at this point
    DELETED = (
        "deleted"
    )  # When a Payout has been manually deleted by someone on the Payments team, Money is still in the Stripe Managed Account balance.
    ERROR = (
        "error"
    )  # When a Payout fails for a systemic issue e.g. Connection/Timeout/RateLimiting

    @classmethod
    def stripe_status_to_transfer_status(cls, stripe_status):
        _stripe_status_to_transfer_mapping = {
            # NOTE: stripe used `canceled`, but we used `cancelled`
            "canceled": TransferStatus.CANCELLED.value,
            "paid": TransferStatus.PAID.value,
            "pending": TransferStatus.PENDING.value,
            "failed": TransferStatus.FAILED.value,
            "in_transit": TransferStatus.IN_TRANSIT.value,
            "created": TransferStatus.CREATED.value,
        }
        return _stripe_status_to_transfer_mapping.get(stripe_status, None)

    @classmethod
    def failed_statuses(cls):
        """
        Returns the statuses considered as failures
        :return: collection of failure TransferStatus(s) values
        """
        return TransferStatus.ERROR.value, TransferStatus.FAILED.value


class TransferStatusCode(object):
    ERROR_AMOUNT_LIMIT_EXCEEDED = "amount_limit_exceeded_error"
    ERROR_NO_GATEWAY_ACCOUNT = "no_gateway_account_error"
    ERROR_GATEWAY_ACCOUNT_SETUP = "gateway_account_setup_error"
    ERROR_AMOUNT_MISMATCH = "amount_mismatch_error"
    ERROR_ACCOUNT_ID_MISMATCH = "account_id_mismatch_error"
    ERROR_SUBMISSION = "gateway_submission_error"
    ERROR_INVALID_STATE = "invalid_state"
    UNKNOWN_ERROR = "unknown_error"
