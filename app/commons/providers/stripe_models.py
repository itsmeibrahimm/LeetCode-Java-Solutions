import pydantic
from typing import Dict, List, NewType, Optional
from enum import Enum
from app.commons.types import CountryCode


# global stripe settings
# hard code this because we'll need code changes anyway to support newer versions
STRIPE_API_VERSION = "2019-05-16"


IdempotencyKey = Optional[str]
SettingsByCountryCode = Dict[CountryCode, "StripeClientSettings"]
SettingsList = List["StripeClientSettings"]
TokenId = NewType("TokenId", str)
CustomerId = NewType("CustomerId", str)
ConnectedAccountId = NewType("ConnectedAccountId", str)
PaymentMethodId = NewType("PaymentMethodId", str)
PaymentIntentId = NewType("PaymentIntentId", str)


class BaseModel(pydantic.BaseModel):
    def dict(self, *, include=None, exclude=None, by_alias=False, skip_defaults=True):
        """
        Generate a dictionary representation of the model, optionally specifying which fields to include or exclude.

        By default, we skip serializing any default (or unset) values
        """
        return super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
        )


class StripeClientSettings(BaseModel):
    # informational
    country: CountryCode

    # stripe settings
    api_key: str
    api_version: Optional[str] = STRIPE_API_VERSION

    @property
    def client_settings(self) -> dict:
        return {"api_key": self.api_key, "stripe_version": self.api_version}


class CreateConnectedAccountToken(BaseModel):
    card: str
    stripe_account: str
    customer: str


class CreateBankAccountToken(BaseModel):
    ...


class CreateCreditCardToken(BaseModel):
    number: str
    exp_month: int
    exp_year: int
    cvc: str


class CreateCustomer(BaseModel):
    email: str
    description: str


class CreatePaymentIntent(BaseModel):
    """
    See: https://stripe.com/docs/api/payment_intents/create
    """

    class CaptureMethod(str, Enum):
        automatic = "automatic"
        manual = "manual"

    class ConfirmationMethod(str, Enum):
        automatic = "automatic"
        manual = "manual"

    class PaymentMethodOptions(BaseModel):
        class CardOptions(BaseModel):
            class RequestThreeDSecure(str, Enum):
                automatic = "automatic"
                any = "any"

            request_three_d_secure: Optional[RequestThreeDSecure]

        card: Optional[CardOptions]

    class TransferData(BaseModel):
        destination: ConnectedAccountId
        amount: Optional[int]

    amount: int
    currency: str
    application_fee_amount: Optional[int]
    capture_method: Optional[CaptureMethod]
    confirm: Optional[bool]
    confirmation_method: Optional[ConfirmationMethod]
    customer: Optional[CustomerId]
    description: Optional[str]
    metadata: Optional[dict]
    off_session: Optional[bool]  # only when confirm=True
    on_behalf_of: Optional[ConnectedAccountId]
    payment_method: Optional[PaymentMethodId]
    payment_method_options: Optional[dict]
    payment_method_types: Optional[str]
    receipt_email: Optional[str]
    return_url: Optional[str]  # only when confirm=True
    save_payment_method: Optional[bool]
    setup_future_usage: Optional[bool]
    shipping: Optional[dict]
    statement_descriptor: Optional[str]
    transfer_data: Optional[TransferData]
    transfer_group: Optional[str]
