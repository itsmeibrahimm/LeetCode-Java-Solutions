from enum import Enum


class StatusType(str, Enum):
    """
    Enum definition of Status of a dispute
    https://stripe.com/docs/api/disputes/object#dispute_object-status
    """

    WARNING_CLOSED = "warning_closed"
    CHARGE_REFUNDED = "charge_refunded"
    WARNING_UNDER_REVIEW = "warning_under_review"
    WON = "won"
    NEEDS_RESPONSE = "needs_response"
    WARNING_NEEDS_RESPONSE = "warning_needs_response"
    LOST = "lost"
    UNDER_REVIEW = "under_review"


class ReasonType(str, Enum):
    """
    Enum definition of Reason of dispute
    https://stripe.com/docs/api/disputes/object#dispute_object-reason
    """

    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    PRODUCT_NOT_RECEIVED = "product_not_received"
    GENERAL = "general"
    PRODUCT_UNACCEPTABLE = "product_unacceptable"
    CREDIT_NOT_PROCESSED = "credit_not_processed"
    FRAUDULENT = "fraudulent"
    UNRECOGNIZED = "unrecognized"
    DUPLICATE = "duplicate"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INCORRECT_ACCOUNT_DETAILS = "incorrect_account_details"
    DEBIT_NOT_AUTHORIZED = "debit_not_authorized"
    CUSTOMER_INITIATED = "customer_initiated"
    CHECK_RETURNED = "check_returned"
    BANK_CANNOT_PROCESS = "bank_cannot_process"


class DisputeIdType(str, Enum):
    """
    Enum definition for the type of dispute id
    """

    STRIPE_DISPUTE_ID = "stripe_dispute_id"
    DD_STRIPE_DISPUTE_ID = "dd_stripe_dispute_id"
