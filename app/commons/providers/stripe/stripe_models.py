from datetime import datetime

import pydantic
from typing import Dict, List, NewType, Optional, Any
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
PaymentIntentStatus = NewType("PaymentIntentStatus", str)


class StripeBaseModel(pydantic.BaseModel):
    # object String that comes from a typical stripe response. Denotes the object 'type'
    # Reference: https://stripe.com/docs/api/events/object#event_object-object
    _STRIPE_OBJECT_NAME: Optional[str] = None

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


class StripeClientSettings(StripeBaseModel):
    # informational
    country: CountryCode

    # stripe settings
    api_key: str
    api_version: Optional[str] = STRIPE_API_VERSION

    @property
    def client_settings(self) -> dict:
        return {"api_key": self.api_key, "stripe_version": self.api_version}


# --------------- REQUEST MODELS ---------------------------------------------------------------------------------------
class CreateConnectedAccountToken(StripeBaseModel):
    card: str
    stripe_account: str
    customer: str


class CreateBankAccountToken(StripeBaseModel):
    ...


class CreateCreditCardToken(StripeBaseModel):
    number: str
    exp_month: int
    exp_year: int
    cvc: str


class CreateCustomer(StripeBaseModel):
    email: str
    description: str


class UpdateCustomer(StripeBaseModel):
    class InvoiceSettings(StripeBaseModel):
        default_payment_method: str

    sid: str
    invoice_settings: InvoiceSettings


class TransferData(StripeBaseModel):
    destination: ConnectedAccountId
    amount: Optional[int]


class CreatePaymentIntent(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/payment_intents/create
    """

    class CaptureMethod(str, Enum):
        AUTOMATIC = "automatic"
        MANUAL = "manual"

    class ConfirmationMethod(str, Enum):
        AUTOMATIC = "automatic"
        MANUAL = "manual"

    class SetupFutureUsage(str, Enum):
        ON_SESSION = "on_session"
        OFF_SESSION = "off_session"

    class PaymentMethodOptions(StripeBaseModel):
        class CardOptions(StripeBaseModel):
            class RequestThreeDSecure(str, Enum):
                AUTOMATIC = "automatic"
                ANY = "any"

            request_three_d_secure: Optional[RequestThreeDSecure]

        card: Optional[CardOptions]

    # TODO Determine how we can use types where Enums are defined.  For example capture_method: Optional[CaptureMethod].
    # If used directly stripe will error out.
    amount: int
    currency: str
    application_fee_amount: Optional[int]
    capture_method: Optional[str]
    confirm: Optional[bool]
    confirmation_method: Optional[str]
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
    setup_future_usage: Optional[str]
    shipping: Optional[dict]
    statement_descriptor: Optional[str]
    transfer_data: Optional[TransferData]
    transfer_group: Optional[str]


class CapturePaymentIntent(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/payment_intents/capture
    """

    sid: PaymentIntentId
    amount_to_capture: Optional[int]
    application_fee_amount: Optional[int]
    statement_descriptor: Optional[str]
    transfer_data: Optional[TransferData]


class CancelPaymentIntent(StripeBaseModel):
    class CancellationReason(str, Enum):
        ABANDONED = "abandoned"
        DUPLICATE = "duplicate"
        FRAUDULENT = "fraudulent"
        REQUESTED_BY_CONSUMER = "requested_by_customer"

    sid: PaymentIntentId
    cancellation_reason: str


class CreatePaymentMethod(StripeBaseModel):
    class Card(StripeBaseModel):
        token: str

    type: str
    card: Card


class AttachPaymentMethod(StripeBaseModel):
    sid: str
    customer: str


class DetachPaymentMethod(StripeBaseModel):
    sid: str


class RetrievePaymentMethod(StripeBaseModel):
    id: str


# --------------- RESPONSE MODELS --------------------------------------------------------------------------------------
class PaymentMethod(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/payment_methods/object
    """

    _STRIPE_OBJECT_NAME: str = "payment_method"

    class Card(StripeBaseModel):
        exp_month: int
        exp_year: int
        fingerprint: str
        last4: str
        funding: Optional[str]
        brand: Optional[str]
        country: Optional[str]
        description: Optional[str]

    class BillingDetails(StripeBaseModel):
        class Address(StripeBaseModel):
            city: Optional[str]
            country: Optional[str]
            line1: Optional[str]
            line2: Optional[str]
            postal_code: Optional[str]
            state: Optional[str]

        address: Optional[Address]
        email: Optional[str]
        name: Optional[str]
        phone: Optional[str]

    id: str
    type: str
    object: Optional[str]
    customer: Optional[str]
    card: Card
    billing_details: BillingDetails


class Event(StripeBaseModel):
    """
    https://stripe.com/docs/api/events
    """

    _STRIPE_OBJECT_NAME: str = "event"

    id: str
    object: str
    account: Optional[str]
    api_version: str
    created: datetime

    class Data(StripeBaseModel):
        object: Dict[str, Any]
        previous_attributes: Optional[Dict[str, Any]]

    data: Data
    livemode: bool
    pending_webhooks: int

    class Request(StripeBaseModel):
        id: Optional[str]
        idempotency_key: Optional[str]

    request: Optional[Request]
    type: str

    @property
    def resource_type(self):
        """
        Reference: https://stripe.com/docs/api/events/object#event_object-type
        :return: str represeting the api resource type in Stripe's API
        """
        return self.data.object.get("object")

    @property
    def event_type(self):
        """
        Reference: https://stripe.com/docs/api/events/object#event_object-type
        :return: str represeting the api resource type in Stripe's API
        """
        split_type = self.type.rsplit(".", 1)
        return split_type[1]

    @property
    def data_object(self):
        return self.data.object
