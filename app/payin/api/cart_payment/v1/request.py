from pydantic import BaseModel, Schema

from app.payin.core.cart_payment.types import CaptureMethod, CartType


class LegacyPayment(BaseModel):
    consumer_id: int = Schema(
        ..., title="DoorDash consumer ID that a payment is being made for."
    )

    stripe_customer_id: int = Schema(
        ..., title="Stripe customer ID that a payment is being made for."
    )

    charge_id: int = Schema(..., title="Legacy charge ID associated with a payment.")


class SplitPayment(BaseModel):
    payout_account_id: str = Schema(..., title="ID of payout account.")

    appication_fee_amount: int = Schema(..., title="Application fee for split payment.")


class CartMetadata(BaseModel):
    reference_id: int = Schema(
        ...,
        title="Identifier of client object that a payment is performed for, such as an order cart.",
    )

    ct_reference_id: int = Schema(
        ..., title="Client defined type for object that a payment is performed for."
    )

    type: CartType = Schema(CartType.ORDER_CART, title="Type of payment.")


class CartPaymentRequest(BaseModel):
    payer_id: str = Schema(
        ..., title="Payment system account ID associated with entity to charge."
    )

    amount: int = Schema(..., title="Amount to charge.")

    country: str = Schema(..., title="Country of origin for payment.")

    currency: str = Schema(..., title="Currency for payment.")

    payment_method_id: str = Schema(
        ..., title="ID of payment method to use for the payment."
    )

    capture_method: CaptureMethod = Schema(
        CaptureMethod.AUTO, title="Charge capture strategy to apply."
    )

    idempotency_key: str = Schema(
        ...,
        title=(
            "Idempotency key.  Provide a unique value for each attempted payment creation attempt.  Only one cart "
            "payment is created for a given (payer_id, idempotency_key)."
        ),
    )

    client_description: str = Schema(
        None,
        title=(
            "Optional string that clients may associate with the charge.  The string is not processed or modified "
            "by the payment system."
        ),
    )

    payer_statement_description: str = Schema(
        None,
        title="Optional string that will appear on the payer's payment method statement (e.g. credit card statement).",
    )

    legacy_payment: LegacyPayment = Schema(
        None,
        title=(
            "Optional object allowing legacy clients to use new payment service API.  This allows caller to provide "
            "legacy identifiers that can be used to create charges."
        ),
    )

    split_payment: SplitPayment = Schema(
        None,
        title="Optional object for describing split payments, where ammount is split between a payer and merchant.",
    )

    metadata: CartMetadata = Schema(
        ..., title="Optional structure that describes additional properites of payment."
    )
