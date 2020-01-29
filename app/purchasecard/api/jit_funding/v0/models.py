from pydantic import BaseModel
from typing import Optional
from app.commons.api.models import PaymentResponse


class CardAcceptor(BaseModel):
    mid: str
    mcc: str
    name: str


class OriginalCurrency(BaseModel):
    conversion_rate: float
    original_amount: float
    original_currency_code: str


class CurrencyConversion(BaseModel):
    network: OriginalCurrency


class Response(BaseModel):
    code: Optional[str]
    memo: Optional[str]


class AddressVerificationRequest(BaseModel):
    zip: Optional[str]
    street_address: Optional[str]


class OnFile(BaseModel):
    zip: Optional[str]
    street_address: Optional[str]


class Issuer(BaseModel):
    response: Optional[Response]
    on_file: Optional[OnFile]


class AddressVerification(BaseModel):
    request: Optional[AddressVerificationRequest]
    issuer: Optional[Issuer]


class JITFunding(BaseModel):
    token: str
    method: str
    user_token: str
    acting_user_token: Optional[str]
    amount: float
    address_verification: Optional[AddressVerification]


class GpaOrder(BaseModel):
    jit_funding: JITFunding


class MarqetaJITFundingRequest(BaseModel):
    token: str
    user_token: str
    card_acceptor: CardAcceptor
    user_transaction_time: str
    amount: float
    currency_code: str
    currency_conversion: Optional[CurrencyConversion]
    gpa_order: GpaOrder


class MarqetaJITFundingResponse(PaymentResponse):
    jit_funding: JITFunding
