#  type: ignore

from datetime import datetime
from typing import Optional

from app.commons.api.models import PaymentResponse, PaymentRequest
from pydantic import Schema
from app.payout.core.instant_payout.models import (
    InstantPayoutStatusType,
    InstantPayoutFees,
    PaymentEligibilityReasons,
)
from app.commons.types import Currency
from app.payout.models import PayoutAccountId


__all__ = ["InstantPayoutCreate", "InstantPayout", "PaymentEligibility"]

################################
# Data Model for API requests  #
################################


class InstantPayoutCreate(PaymentRequest):
    """Request model for creating a instant payout."""

    payout_account_id: PayoutAccountId = Schema(
        default=...,
        description="The payment account id under which the instant payout to be created.",
    )
    amount: int = Schema(
        default=..., description="The amount of instant payout in cents, without fee."
    )
    currency: Currency = Schema(
        default=..., description="The currency code for the transaction to be created."
    )
    card: Optional[str] = Schema(
        default=None,
        description="(Optional) The payout card to instant payout to. If not provided, use default payout card.",
    )


################################
# Data Model for API response  #
################################


class InstantPayout(PaymentResponse):
    payout_account_id: PayoutAccountId = Schema(
        default=..., description="The payment account id."
    )
    payout_id: int = Schema(default=..., description="Instant Payout Id.")
    amount: int = Schema(default=..., description="The amount of the Instant Payout.")
    currency: Currency = Schema(
        default=..., description="The currency of the Instant Payout."
    )
    fee: InstantPayoutFees = Schema(
        default=..., description="The fee of the Instant Payout."
    )
    status: InstantPayoutStatusType = Schema(
        default=..., description="Status of the Instant Payout."
    )
    card: str = Schema(
        default=..., description="The payout card of the Instant Payout."
    )
    created_at: datetime = Schema(
        default=..., description="Created time of the Instant Payout."
    )


class PaymentEligibility(PaymentResponse):
    payout_account_id: PayoutAccountId = Schema(
        default=..., description="The payment account id."
    )
    eligible: bool = Schema(
        default=..., description="Eligible status for instant payout."
    )
    reason: Optional[PaymentEligibilityReasons] = Schema(
        default=..., description="The reason when instant payout is ineligible."
    )
    details: Optional[str] = Schema(
        default=..., description="Detailed info if instant payout is ineligible."
    )
    balance: Optional[int] = Schema(
        default=..., description="Available balance to be paid out."
    )
    currency: Optional[Currency] = Schema(
        default=..., description="Currency of the balance."
    )
    fee: Optional[InstantPayoutFees] = Schema(
        default=..., description="Instant payout fee."
    )
