from enum import Enum
from typing import Any, Dict, Optional, List, Union

from pydantic import BaseModel
from stripe.error import StripeError
from structlog.stdlib import BoundLogger

from app.commons.context.logger import get_logger

__all__ = [
    "StripeErrorCode",
    "StripeDeclineCode",
    "StripeErrorParser",
    "StripeInvalidParam",
    "StripeErrorType",
]

log: BoundLogger = get_logger(__name__)


class StripeErrorType(str, Enum):
    """
    A collection of stripe error types.
    https://stripe.com/docs/api/errors
    """

    api_connection_error = "api_connection_error"
    api_error = "api_error"
    authentication_error = "authentication_error"
    card_error = "card_error"
    idempotency_error = "idempotency_error"
    invalid_request_error = "invalid_request_error"
    rate_limit_error = "rate_limit_error"
    validation_error = "validation_error"


class StripeErrorCode(str, Enum):
    """
    A strong typed Stripe Error Codes.
    Collected from: https://stripe.com/docs/error-codes
    """

    account_already_exists = "account_already_exists"
    account_country_invalid_address = "account_country_invalid_address"
    account_invalid = "account_invalid"
    account_number_invalid = "account_number_invalid"
    alipay_upgrade_required = "alipay_upgrade_required"
    amount_too_large = "amount_too_large"
    amount_too_small = "amount_too_small"
    api_key_expired = "api_key_expired"
    authentication_required = "authentication_required"
    balance_insufficient = "balance_insufficient"
    bank_account_declined = "bank_account_declined"
    bank_account_exists = "bank_account_exists"
    bank_account_unusable = "bank_account_unusable"
    bank_account_unverified = "bank_account_unverified"
    bank_account_verification_failed = "bank_account_verification_failed"
    bitcoin_upgrade_required = "bitcoin_upgrade_required"
    card_declined = "card_declined"
    charge_already_captured = "charge_already_captured"
    charge_already_refunded = "charge_already_refunded"
    charge_disputed = "charge_disputed"
    charge_exceeds_source_limit = "charge_exceeds_source_limit"
    charge_expired_for_capture = "charge_expired_for_capture"
    charge_invalid_parameter = "charge_invalid_parameter"
    country_unsupported = "country_unsupported"
    coupon_expired = "coupon_expired"
    customer_max_subscriptions = "customer_max_subscriptions"
    email_invalid = "email_invalid"
    expired_card = "expired_card"
    idempotency_key_in_use = "idempotency_key_in_use"
    incorrect_address = "incorrect_address"
    incorrect_cvc = "incorrect_cvc"
    incorrect_number = "incorrect_number"
    incorrect_zip = "incorrect_zip"
    instant_payouts_unsupported = "instant_payouts_unsupported"
    invalid_card_type = "invalid_card_type"
    invalid_charge_amount = "invalid_charge_amount"
    invalid_cvc = "invalid_cvc"
    invalid_expiry_month = "invalid_expiry_month"
    invalid_expiry_year = "invalid_expiry_year"
    invalid_number = "invalid_number"
    invalid_source_usage = "invalid_source_usage"
    invoice_no_customer_line_items = "invoice_no_customer_line_items"
    invoice_no_subscription_line_items = "invoice_no_subscription_line_items"
    invoice_not_editable = "invoice_not_editable"
    invoice_payment_intent_requires_action = "invoice_payment_intent_requires_action"
    invoice_upcoming_none = "invoice_upcoming_none"
    livemode_mismatch = "livemode_mismatch"
    lock_timeout = "lock_timeout"
    missing = "missing"
    not_allowed_on_standard_account = "not_allowed_on_standard_account"
    order_creation_failed = "order_creation_failed"
    order_required_settings = "order_required_settings"
    order_status_invalid = "order_status_invalid"
    order_upstream_timeout = "order_upstream_timeout"
    out_of_inventory = "out_of_inventory"
    parameter_invalid_empty = "parameter_invalid_empty"
    parameter_invalid_integer = "parameter_invalid_integer"
    parameter_invalid_string_blank = "parameter_invalid_string_blank"
    parameter_invalid_string_empty = "parameter_invalid_string_empty"
    parameter_missing = "parameter_missing"
    parameter_unknown = "parameter_unknown"
    parameters_exclusive = "parameters_exclusive"
    payment_intent_authentication_failure = "payment_intent_authentication_failure"
    payment_intent_incompatible_payment_method = (
        "payment_intent_incompatible_payment_method"
    )
    payment_intent_invalid_parameter = "payment_intent_invalid_parameter"
    payment_intent_payment_attempt_failed = "payment_intent_payment_attempt_failed"
    payment_intent_unexpected_state = "payment_intent_unexpected_state"
    payment_method_unactivated = "payment_method_unactivated"
    payment_method_unexpected_state = "payment_method_unexpected_state"
    payouts_not_allowed = "payouts_not_allowed"
    platform_api_key_expired = "platform_api_key_expired"
    postal_code_invalid = "postal_code_invalid"
    processing_error = "processing_error"
    product_inactive = "product_inactive"
    rate_limit = "rate_limit"
    resource_already_exists = "resource_already_exists"
    resource_missing = "resource_missing"
    routing_number_invalid = "routing_number_invalid"
    secret_key_required = "secret_key_required"
    sepa_unsupported_account = "sepa_unsupported_account"
    setup_attempt_failed = "setup_attempt_failed"
    setup_intent_authentication_failure = "setup_intent_authentication_failure"
    setup_intent_unexpected_state = "setup_intent_unexpected_state"
    shipping_calculation_failed = "shipping_calculation_failed"
    sku_inactive = "sku_inactive"
    state_unsupported = "state_unsupported"
    tax_id_invalid = "tax_id_invalid"
    taxes_calculation_failed = "taxes_calculation_failed"
    testmode_charges_only = "testmode_charges_only"
    tls_version_unsupported = "tls_version_unsupported"
    token_already_used = "token_already_used"
    token_in_use = "token_in_use"
    transfers_not_allowed = "transfers_not_allowed"
    upstream_order_creation_failed = "upstream_order_creation_failed"
    url_invalid = "url_invalid"

    @classmethod
    def get_or_none(cls, value: str) -> Optional["StripeErrorCode"]:
        if value in cls._value2member_map_:
            return cls(value)
        return None


class StripeDeclineCode(str, Enum):
    """
    A strong typed Stripe Decline Code.
    Collected from https://stripe.com/docs/declines/codes
    """

    authentication_required = "authentication_required"
    approve_with_id = "approve_with_id"
    call_issuer = "call_issuer"
    card_not_supported = "card_not_supported"
    card_velocity_exceeded = "card_velocity_exceeded"
    currency_not_supported = "currency_not_supported"
    do_not_honor = "do_not_honor"
    do_not_try_again = "do_not_try_again"
    duplicate_transaction = "duplicate_transaction"
    expired_card = "expired_card"
    fraudulent = "fraudulent"
    generic_decline = "generic_decline"
    incorrect_number = "incorrect_number"
    incorrect_cvc = "incorrect_cvc"
    incorrect_pin = "incorrect_pin"
    incorrect_zip = "incorrect_zip"
    insufficient_funds = "insufficient_funds"
    invalid_account = "invalid_account"
    invalid_amount = "invalid_amount"
    invalid_cvc = "invalid_cvc"
    invalid_expiry_year = "invalid_expiry_year"
    invalid_number = "invalid_number"
    invalid_pin = "invalid_pin"
    issuer_not_available = "issuer_not_available"
    lost_card = "lost_card"
    merchant_blacklist = "merchant_blacklist"
    new_account_information_available = "new_account_information_available"
    no_action_taken = "no_action_taken"
    not_permitted = "not_permitted"
    offline_pin_required = "offline_pin_required"
    online_or_offline_pin_required = "online_or_offline_pin_required"
    pickup_card = "pickup_card"
    pin_try_exceeded = "pin_try_exceeded"
    processing_error = "processing_error"
    reenter_transaction = "reenter_transaction"
    restricted_card = "restricted_card"
    revocation_of_all_authorizations = "revocation_of_all_authorizations"
    revocation_of_authorization = "revocation_of_authorization"
    security_violation = "security_violation"
    service_not_allowed = "service_not_allowed"
    stolen_card = "stolen_card"
    stop_payment_order = "stop_payment_order"
    testmode_decline = "testmode_decline"
    transaction_not_allowed = "transaction_not_allowed"
    try_again_later = "try_again_later"
    withdrawal_count_limit_exceeded = "withdrawal_count_limit_exceeded"

    @classmethod
    def get_or_none(cls, value) -> Optional["StripeDeclineCode"]:
        if value in cls._value2member_map_:
            return cls(value)
        return None


class StripeInvalidParam(str, Enum):
    """
    Possible invalid params identified on Stripe server end and raised with stripe.InvalidRequestError
    !!Note!! there is no exhausted list on this yet, please add entries here as you observe and need
    """

    payment_method = "payment_method"

    @classmethod
    def get_or_none(cls, value: str) -> Optional["StripeInvalidParam"]:
        if value in cls._value2member_map_:
            return cls(value)
        return None


class _StripeErrorDetails(BaseModel):
    class Config:
        allow_mutation = False

    message: Optional[str]
    code: Optional[str]
    type: Optional[str]
    decline_code: Optional[str]
    charge: Optional[str]
    payment_intent: Optional[Dict[str, Any]]
    param: Optional[Union[str, List[str]]]


class StripeErrorParser:
    """
    Utility class to strong type StripeError.json_body["error"] structure.
    """

    _details: _StripeErrorDetails
    error: StripeError

    def __init__(self, stripe_error: StripeError):
        self.error = stripe_error
        self._details = StripeErrorParser._parse_details(stripe_error)

    @property
    def code(self) -> str:
        # If we were not able to get code and message from parsing error blob
        # we can utilize StripeError.code to populate these data
        # Stripe python sdk handle code parsing out of http response differently
        # than common api exceptions
        # see: https://github.com/stripe/stripe-python/blob/master/stripe/api_requestor.py#L125-L152
        return (
            self._details.code
            if self._details and self._details.code
            else self.error.code
        )

    @property
    def message(self) -> str:
        return str(self.error) or self._details.message or ""

    @property
    def has_details(self) -> bool:
        return len(self._details.__fields_set__) > 0

    @property
    def type(self) -> Optional[str]:
        return self._details.type

    @property
    def payment_intent_data(self) -> Dict[str, Any]:
        return self._details.payment_intent or {}

    @property
    def decline_code(self) -> Optional[str]:
        return self._details.decline_code

    @property
    def charge_id(self) -> Optional[str]:
        return self._details.charge

    def has_invalid_param(self, param: StripeInvalidParam) -> bool:
        """
        Args:
            param (StripeInvalidParam): whether given invalid param is in the error
        Returns:
            whether given invalid param is in the error
        """
        known_invalid_params = self._details.param
        if known_invalid_params:
            if isinstance(known_invalid_params, list):
                return bool(param in known_invalid_params)
            return param == known_invalid_params
        return False

    @staticmethod
    def _parse_details(stripe_error: StripeError) -> _StripeErrorDetails:
        details = None
        # Best effort to parse StripeError.json_body["error"] if the error blob
        # was returned as dict structure
        if stripe_error.json_body and isinstance(stripe_error.json_body, dict):
            error_data = stripe_error.json_body.get("error", {})
            if isinstance(error_data, dict):
                details = _StripeErrorDetails.parse_obj(error_data)

        return details or _StripeErrorDetails()
