from typing import Optional

from pydantic import BaseModel, PositiveInt, ConstrainedStr

from app.commons.types import CountryCode, CurrencyType
from app.commons.types import CountryCode


class PayerStatementDescription(ConstrainedStr):
    """
    String used for statement descriptor field, with restricted max length according to what providers support.
    """

    max_length = 22


class SplitPayment(BaseModel):
    payout_account_id: str
    application_fee_amount: int


class CreateCartPaymentBaseRequest(BaseModel):
    amount: PositiveInt
    payment_country: CountryCode
    currency: CurrencyType
    delay_capture: bool
    idempotency_key: str
    client_description: Optional[str] = None
    payer_statement_description: Optional[PayerStatementDescription] = None
    split_payment: Optional[SplitPayment] = None


class UpdateCartPaymentBaseRequest(BaseModel):
    idempotency_key: str
    amount: PositiveInt
    client_description: Optional[str] = None
