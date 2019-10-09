from typing import Optional

from pydantic import BaseModel, PositiveInt, ConstrainedStr

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


class SplitPayment(BaseModel):
    # For V0/V1, we expect clients to provide the connect account ID inside the payout_account_id field.
    # For future API versions, clients will provide the payment-service's payout account ID here, in which
    # case we can look up the corresponding provider resource ID inside our service.
    payout_account_id: str
    application_fee_amount: int


class CreateCartPaymentBaseRequest(BaseModel):
    amount: PositiveInt
    payment_country: CountryCode
    currency: Currency
    delay_capture: bool
    idempotency_key: str
    payer_statement_description: Optional[PayerStatementDescription] = None
    split_payment: Optional[SplitPayment] = None


class UpdateCartPaymentBaseRequest(BaseModel):
    idempotency_key: str
    amount: PositiveInt
    client_description: Optional[str] = None
    split_payment: Optional[SplitPayment] = None


class CancelCartPaymentRequest(BaseModel):
    pass
