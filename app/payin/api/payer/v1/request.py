from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Schema

from app.commons.types import CountryCode
from app.payin.core.payer.model import PayerCorrelationIds


class CreatePayerRequest(BaseModel):
    """
    Request to create a payer.
    """

    payer_correlation_ids: PayerCorrelationIds = Schema(  # type: ignore
        default=..., description="payer correlation ids"
    )
    email: str = Schema(  # type: ignore
        default=...,
        description="email for client used when we create external account on payment provider",
    )
    country: CountryCode = Schema(  # type: ignore
        default=CountryCode.US, description="country where payer is located"
    )
    description: str = Schema(  # type: ignore
        default=..., description="description of payer"
    )


class DefaultPaymentMethodV1(BaseModel):
    """
    Define the pair of payment method id.
    """

    payment_method_id: Optional[UUID] = Schema(  # type: ignore
        default=..., description="identity of the payment method."
    )
    # first-class support for dd_stripe_card_id in v1 API because we can't backfill all the existing Cx's card objects.
    dd_stripe_card_id: Optional[str] = Schema(  # type: ignore
        default=..., description="legacy identity of StripeCard object"
    )


class UpdatePayerRequestV1(BaseModel):
    """
    Request to update a payer's information.
    """

    default_payment_method: DefaultPaymentMethodV1 = Schema(  # type: ignore
        default=...,
        description="object that contains a pair of payer's default payment method id",
    )
