from typing import Optional

from pydantic import BaseModel, PositiveInt, ConstrainedInt, ConstrainedStr, Schema

from app.commons.types import CountryCode, Currency
from app.commons.types import CountryCode


class PayerStatementDescription(ConstrainedStr):
    """
    String used for statement_descriptor field, with restricted max length according to what providers support.
    """

    max_length = 22


class ClientDescription(ConstrainedStr):
    """
    String used for client_description field, with restricted max length according to what providers support.
    """

    max_length = 1000


class UpdateAmount(ConstrainedInt):
    """
    Int used for updating a cart payment amount.  Allows zero or higher to be provided.
    """

    ge = 0


class SplitPayment(BaseModel):
    # For V0/V1, we expect clients to provide the connect account ID inside the payout_account_id field.
    # For future API versions, clients will provide the payment-service's payout account ID here, in which
    # case we can look up the corresponding provider resource ID inside our service.
    payout_account_id: str = Schema(  # type: ignore
        default=..., description="destination of split payment funds transfer"
    )
    application_fee_amount: int = Schema(  # type: ignore
        default=...,
        description="amount of fees collected from destination payout account to DoorDash",
    )


class CreateCartPaymentBaseRequest(BaseModel):
    amount: PositiveInt = Schema(  # type: ignore
        default=..., description="amount of this payment, should be positive number"
    )
    payment_country: CountryCode = Schema(  # type: ignore
        default=..., description="country of this payment"
    )
    currency: Currency = Schema(
        default=..., description="payment currency"
    )  # type: ignore
    delay_capture: bool = Schema(  # type: ignore
        default=...,
        description="whether create this payment with separate auth and capture",
    )
    idempotency_key: str = Schema(  # type: ignore
        default=...,
        description="client should retry with same idempotency key to avoid double charge",
    )
    payer_statement_description: Optional[
        PayerStatementDescription
    ] = Schema(  # type: ignore
        default=None, description="payer's bank statement description"
    )
    split_payment: Optional[SplitPayment] = Schema(  # type: ignore
        default=None,
        description="define if the payment funds need to flow separately to DoorDash account and Mx account",
    )


class UpdateCartPaymentBaseRequest(BaseModel):
    idempotency_key: str
    amount: UpdateAmount
    client_description: Optional[str] = None
    split_payment: Optional[SplitPayment] = None
