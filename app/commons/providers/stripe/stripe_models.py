from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, NewType, Optional

import pydantic

from app.commons.providers.stripe.types import StripePlatformAccountId
from app.commons.types import CountryCode

# global stripe settings
# hard code this because we'll need code changes anyway to support newer versions
from app.payout.constants import (
    CREATE_STRIPE_ACCOUNT_TYPE,
    CREATE_STRIPE_ACCOUNT_REQUESTED_CAPABILITIES,
)
from app.payout.types import (
    PayoutMethodExternalAccountToken,
    PayoutType,
    PgpExternalAccountId,
    StripeAccountToken,
    StripeBusinessType,
    StripeFileHandle,
)

STRIPE_API_VERSION = "2019-10-08"


IdempotencyKey = Optional[str]
SettingsByCountryCode = Dict[CountryCode, "StripeClientSettings"]
SettingsList = List["StripeClientSettings"]
TokenId = NewType("TokenId", str)
CustomerId = NewType("CustomerId", str)
ConnectedAccountId = NewType("ConnectedAccountId", str)
PaymentMethodId = NewType("PaymentMethodId", str)
PaymentIntentId = NewType("PaymentIntentId", str)
PaymentIntentStatus = NewType("PaymentIntentStatus", str)
StripeDisputeId = NewType("StripeDisputeId", str)
Currency = NewType("Currency", str)
Amount = NewType("Amount", int)
Destination = NewType("Destination", str)
StatementDescriptor = NewType("StatementDescriptor", str)
StripeAccountId = NewType("StripeAccountId", str)
Metadata = NewType("Metadata", dict)
TransferId = NewType("TransferId", str)


class StripeBaseModel(pydantic.BaseModel):
    class Config:
        use_enum_values = True

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
class InvoiceSettings(StripeBaseModel):
    default_payment_method: str


class StripeCreateCustomerRequest(StripeBaseModel):
    email: str
    description: str


class StripeRetrieveCustomerRequest(StripeBaseModel):
    id: str


class StripeUpdateCustomerRequest(StripeBaseModel):
    sid: str
    invoice_settings: InvoiceSettings


class TransferData(StripeBaseModel):
    destination: ConnectedAccountId
    amount: Optional[int]


class StripeCreatePaymentIntentRequest(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/payment_intents/create
    """

    class CaptureMethod(str, Enum):
        AUTOMATIC = "automatic"
        MANUAL = "manual"

    class SetupFutureUsage(str, Enum):
        ON_SESSION = "on_session"
        OFF_SESSION = "off_session"

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
    metadata: Optional[Dict[str, Any]]
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


class StripeCapturePaymentIntentRequest(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/payment_intents/capture
    """

    sid: PaymentIntentId
    amount_to_capture: Optional[int]
    application_fee_amount: Optional[int]
    statement_descriptor: Optional[str]
    transfer_data: Optional[TransferData]


class StripeCancelPaymentIntentRequest(StripeBaseModel):
    class CancellationReason(str, Enum):
        ABANDONED = "abandoned"
        DUPLICATE = "duplicate"
        FRAUDULENT = "fraudulent"
        REQUESTED_BY_CONSUMER = "requested_by_customer"

    sid: PaymentIntentId
    cancellation_reason: str


class StripeRefundChargeRequest(StripeBaseModel):
    class RefundReason(str, Enum):
        DUPLICATE = "duplicate"
        FRAUDULENT = "fraudulent"
        REQUESTED_BY_CONSUMER = "requested_by_customer"

    charge: str
    amount: Optional[int]
    metadata: Optional[Dict]
    reason: Optional[str]
    refund_application_fee: Optional[bool]
    reverse_transfer: Optional[bool]


class StripeCreatePaymentMethodRequest(StripeBaseModel):
    class Type(str, Enum):
        CARD = "card"

    class TokenizedCard(StripeBaseModel):
        token: str

    type: Type
    card: TokenizedCard


class StripeAttachPaymentMethodRequest(StripeBaseModel):
    payment_method: str
    customer: str


class StripeDetachPaymentMethodRequest(StripeBaseModel):
    payment_method: str


class StripeRetrievePaymentMethodRequest(StripeBaseModel):
    id: str


class StripeRetrievePayoutRequest(StripeBaseModel):
    id: str
    stripe_account: str


class StripeCancelPayoutRequest(StripeBaseModel):
    sid: str
    stripe_account: str


class StripeUpdateDisputeRequest(StripeBaseModel):
    class Evidence(StripeBaseModel):
        access_activity_log: Optional[str] = None
        billing_address: Optional[str] = None
        cancellation_policy: Optional[str] = None
        cancellation_policy_disclosure: Optional[str] = None
        cancellation_rebuttal: Optional[str] = None
        customer_communication: Optional[str] = None
        customer_email_address: Optional[str] = None
        customer_name: Optional[str] = None
        customer_purchase_ip: Optional[str] = None
        customer_signature: Optional[str] = None
        duplicate_charge_documentation: Optional[str] = None
        duplicate_charge_explanation: Optional[str] = None
        duplicate_charge_id: Optional[str] = None
        product_description: Optional[str] = None
        receipt: Optional[str] = None
        refund_policy: Optional[str] = None
        refund_policy_disclosure: Optional[str] = None
        refund_refusal_explanation: Optional[str] = None
        service_date: Optional[str] = None
        service_documentation: Optional[str] = None
        shipping_address: Optional[str] = None
        shipping_carrier: Optional[str] = None
        shipping_date: Optional[str] = None
        shipping_documentation: Optional[str] = None
        shipping_tracking_number: Optional[str] = None
        uncategorized_file: Optional[str] = None
        uncategorized_text: Optional[str] = None

    sid: str
    evidence: Evidence


class StripeCreateTransferRequest(StripeBaseModel):
    description: Optional[str]
    metadata: Optional[Dict]
    source_transaction: Optional[str]
    source_type: Optional[str]
    transfer_group: Optional[str]


class StripeCreatePayoutRequest(StripeBaseModel):
    description: Optional[str]
    destination: Optional[str]
    metadata: Optional[Dict]
    method: Optional[str]
    source_type: Optional[str]
    statement_descriptor: Optional[str]


class StripeCreateCardRequest(StripeBaseModel):
    customer: CustomerId
    source: TokenId


class Address(StripeBaseModel):
    city: Optional[str]
    country: Optional[str]
    line1: Optional[str]
    line2: Optional[str]
    postal_code: Optional[str]
    state: Optional[str]


class DateOfBirth(StripeBaseModel):
    day: int
    month: int
    year: int


class Document(StripeBaseModel):
    back: Optional[StripeFileHandle]
    front: Optional[StripeFileHandle]
    details: Optional[str]
    details_code: Optional[str]


class Verification(StripeBaseModel):
    additional_document: Document
    details: Optional[str]
    details_code: Optional[str]
    document: Document
    status: str


class Company(StripeBaseModel):
    address: Optional[Address]
    name: Optional[str]
    phone: Optional[str]
    tax_id: Optional[str]
    verification: Optional[Verification]


class Individual(StripeBaseModel):
    address: Optional[Address]
    dob: Optional[DateOfBirth]
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    id_number: Optional[str]
    phone: Optional[str]
    ssn_last_4: Optional[str]
    verification: Optional[Verification]


class CreateAccountTokenMetaDataRequest(StripeBaseModel):
    business_type: Optional[str]
    company: Optional[Company]
    individual: Optional[Individual]
    tos_shown_and_accepted: bool = True


class CreateAccountTokenRequest(StripeBaseModel):
    country: CountryCode
    account: CreateAccountTokenMetaDataRequest


class CreateAccountRequest(StripeBaseModel):
    country: CountryCode
    type: str = CREATE_STRIPE_ACCOUNT_TYPE
    account_token: StripeAccountToken
    requested_capabilities: list = CREATE_STRIPE_ACCOUNT_REQUESTED_CAPABILITIES


class UpdateAccountRequest(StripeBaseModel):
    id: StripeAccountId
    country: CountryCode
    account_token: StripeAccountToken


class CreateExternalAccountRequest(StripeBaseModel):
    country: CountryCode
    type: str
    stripe_account_id: PgpExternalAccountId
    external_account_token: PayoutMethodExternalAccountToken


class ClonePaymentMethodRequest(StripeBaseModel):
    payment_method: PaymentMethodId
    stripe_account: StripePlatformAccountId
    customer: CustomerId


class RetrieveAccountRequest(StripeBaseModel):
    country: CountryCode
    account_id: str


# --------------- RESPONSE MODELS --------------------------------------------------------------------------------------
class BillingDetails(StripeBaseModel):
    address: Address
    email: Optional[str]
    name: Optional[str]
    phone: Optional[str]


class Shipping(StripeBaseModel):
    address: Optional[Address]
    carrier: Optional[str]
    name: Optional[str]
    phone: Optional[str]
    tracking_nubmer: Optional[str]


class PaymentMethodOptions(StripeBaseModel):
    class CardOptions(StripeBaseModel):
        class RequestThreeDSecure(str, Enum):
            automatic = "automatic"
            any = "any"

        request_three_d_secure: Optional[RequestThreeDSecure]

    card: Optional[CardOptions]


class Outcome(StripeBaseModel):
    network_status: str
    reason: str
    risk_level: str
    risk_score: int
    rule: str
    seller_message: str
    type: str


class Customer(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/customers/object
    """

    id: CustomerId
    object: str
    created: datetime
    currency: str
    invoice_settings: InvoiceSettings
    default_source: str
    description: str
    email: str


class PaymentMethod(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/payment_methods/object
    """

    _STRIPE_OBJECT_NAME: str = "payment_method"

    class Card(StripeBaseModel):
        class Wallet(StripeBaseModel):
            type: str
            dynamic_last4: str

        class Checks(StripeBaseModel):
            address_line1_check: Optional[str]
            address_postal_code_check: Optional[str]
            cvc_check: Optional[str]

        exp_month: int
        exp_year: int
        fingerprint: str
        last4: str
        checks: Checks
        funding: Optional[str]
        brand: Optional[str]
        country: Optional[str]
        description: Optional[str]
        wallet: Optional[Wallet]
        state: Optional[str]

    id: str
    type: str
    card: Card
    billing_details: BillingDetails
    object: Optional[str]
    customer: Optional[str]


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


class Refund(StripeBaseModel):
    """
    https://stripe.com/docs/api/refunds
    """

    _STRIPE_OBJECT_NAME: str = "refund"

    id: str
    object: str
    amount: int
    balance_transaction: Optional[str]
    charge: str
    created: int
    currency: str
    metadata: Optional[Dict]
    reason: Optional[str]
    receipt_number: Optional[str]
    source_transfer_reversal: Optional[str]
    status: str
    transfer_reversal: Optional[str]


class Charge(StripeBaseModel):
    """
    https://stripe.com/docs/api/charges
    """

    _STRIPE_OBJECT_NAME: str = "charge"

    id: str
    object: str
    amount: int
    amount_refunded: int
    # amount_updates - preview feature
    application: str
    application_fee: str
    application_fee_amount: int
    balance_transaction: str
    billing_details: Optional[BillingDetails]
    captured: bool
    created: datetime
    currency: str
    customer: str
    description: Optional[str]
    dispute: Optional[str]
    failure_code: Optional[str]
    failure_message: Optional[str]
    invoice: Optional[str]
    livemode: bool
    metadata: Optional[Dict]
    on_behalf_of: Optional[str]
    order: Optional[str]
    outcome: Optional[Outcome]
    paid: bool
    payment_intent: Optional[str]
    payment_method: Optional[str]
    # TODO payment_method_details
    receipt_email: Optional[str]
    receipt_number: Optional[str]
    receipt_url: Optional[str]
    refunded: bool
    # TODO refunds
    review: Optional[str]
    shipping: Optional[Shipping]
    source_transfer: Optional[str]
    statement_descriptor: Optional[str]
    statement_descriptor_suffix: Optional[str]
    status: str
    transfer: Optional[str]
    transfer_data: Optional[TransferData]
    transfer_group: Optional[str]


class PaymentIntent(StripeBaseModel):
    """
    https://stripe.com/docs/api/payment_intents
    """

    _STRIPE_OBJECT_NAME: str = "payment_intent"

    class NextAction(StripeBaseModel):
        class RedirectToUrl(StripeBaseModel):
            return_url: str
            url: str

        redirect_to_url: RedirectToUrl
        type: str
        use_stripe_sdk: str

    class LastPaymentError(StripeBaseModel):
        charge: Optional[str]
        code: Optional[str]
        decline_code: Optional[str]
        doc_url: Optional[str]
        message: Optional[str]
        param: Optional[str]
        payment_method: Optional[PaymentMethod]
        type: Optional[str]

    class Charges(StripeBaseModel):
        data: List[Charge]
        has_more: bool
        object: str
        url: Optional[str]

    id: str
    object: str
    amount: int
    amount_capturable: Optional[int]
    amount_received: Optional[int]
    application: Optional[str]
    application_fee_amount: Optional[int]
    canceled_at: Optional[datetime]
    cancellation_reason: Optional[str]
    capture_method: str
    charges: Charges
    created: datetime
    currency: str
    customer: str
    description: Optional[str]
    invoice: Optional[str]
    last_payment_error: Optional[LastPaymentError]
    livemode: bool
    metadata: Optional[dict]
    next_action: Optional[NextAction]
    on_behalf_of: str
    payment_method: str
    payment_method_options: Optional[PaymentMethodOptions]
    payment_method_types: List[str]
    receipt_email: str
    review: str
    setup_future_usage: str
    shipping: Optional[Shipping]
    statement_descriptor: Optional[str]
    status: str
    transfer_data: Optional[TransferData]
    transfer_group: Optional[str]


class TransferReversal(StripeBaseModel):
    id: str
    object: str
    amount: int
    balanced_transaction: str
    created: datetime
    currency: str
    destination_payment_refund: str
    metadata: dict
    source_refund: str
    transfer: str


class Transfer(StripeBaseModel):
    class Reversals(StripeBaseModel):
        data: List[TransferReversal]
        has_more: bool
        object: str
        url: Optional[str]

    id: str
    object: str
    amount: int
    amount_reversed: int
    balance_transaction: str
    created: datetime
    currency: str
    description: str
    destination: str
    destination_payment: str
    livemode: bool
    metadata: dict
    reversals: Reversals
    reversed: bool
    source_transaction: str
    source_type: str
    transfer_group: str


class Payout(StripeBaseModel):
    id: str
    object: str
    amount: int
    arrival_date: datetime
    automatic: bool
    balance_transaction: str
    created: datetime
    currency: str
    description: str
    destination: str
    failure_balance_transaction: str
    failure_code: str
    failure_message: str
    livemode: bool
    metadata: dict
    method: str
    source_type: str
    statement_descriptor: str
    status: str
    type: str


class SourceTypes(StripeBaseModel):
    card: int


class Balance(StripeBaseModel):
    class Available(StripeBaseModel):
        amount: int
        currency: str
        source_types: SourceTypes

    class ConnectReserved(StripeBaseModel):
        amount: int
        currency: str
        source_types: SourceTypes

    class Pending(StripeBaseModel):
        amount: int
        currency: str
        source_types: SourceTypes

    object: str
    available: List[Available]
    connect_reserved: List[ConnectReserved]
    livemode: bool
    pending: List[Pending]


class Token(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/tokens/object
    """

    _STRIPE_OBJECT_NAME: str = "token"

    id: str
    object: str
    type: str
    used: bool
    created: datetime


class ExternalAccountsList(StripeBaseModel):
    _STRIPE_OBJECT_NAME: str = "list"

    object: str
    data: List[dict]
    has_more: bool
    url: str


class Person(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/persons/object
    """

    _STRIPE_OBJECT_NAME: str = "person"

    id: str
    object: str
    account: str
    address: Optional[Address]
    created: datetime
    dob: Optional[DateOfBirth]
    email: Optional[str]
    first_name: Optional[str]
    gender: Optional[str]
    id_number_provided: bool
    last_name: Optional[str]
    maiden_name: Optional[str]
    metadata: Optional[dict]
    phone: Optional[str]
    relationship: Optional[dict]
    requirements: Optional[dict]
    ssn_last_4_provided: bool
    verification: Optional[Verification]


class Account(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/accounts/object
    """

    _STRIPE_OBJECT_NAME: str = "account"

    id: str
    object: str
    business_profile: Optional[dict]
    business_type: StripeBusinessType
    capabilities: Optional[dict]
    charges_enabled: bool
    company: Optional[dict]
    country: CountryCode
    created: datetime
    default_currency: Currency
    details_submitted: bool
    email: Optional[str]
    external_accounts: Optional[ExternalAccountsList]
    individual: Optional[Person]
    metadata: Optional[dict]
    payouts_enabled: bool
    requirements: Optional[dict]
    settings: Optional[dict]
    tos_acceptance: Optional[dict]
    type: str


class StripeCard(StripeBaseModel):
    """
    See: https://stripe.com/docs/api/external_accounts
    """

    _STRIPE_OBJECT_NAME: str = "card"

    class AddressCheck(str, Enum):
        PASS = ("pass",)
        FAIL = ("fail",)
        UNAVAILABLE = "unavailable"
        UNCHECKED = "unchecked"

    class FundingType(str, Enum):
        CREDIT = "credit"
        DEBIT = "debit"
        PREPAID = "prepaid"
        UNKNOWN = "unknown"

    id: str
    object: str
    account: PgpExternalAccountId
    address_city: Optional[str]
    address_country: Optional[str]
    address_line1: Optional[str]
    address_line1_check: Optional[AddressCheck]
    address_line2: Optional[str]
    address_state: Optional[str]
    address_zip: Optional[str]
    address_zip_check: Optional[AddressCheck]
    available_payout_methods: List[PayoutType] = []
    brand: str
    country: CountryCode
    currency: Currency
    customer: Optional[str]
    cvc_check: Optional[AddressCheck]
    default_for_currency: Optional[bool]
    dynamic_last4: Optional[str]
    exp_month: int
    exp_year: int
    fingerprint: str
    funding: Optional[FundingType]
    last4: str
    metadata: Optional[dict]
    name: Optional[str]
    recipient: Optional[str]
    tokenization_method: Optional[str]


class CardToken(Token):
    """
    See: https://stripe.com/docs/api/tokens/object
    """

    card: StripeCard
