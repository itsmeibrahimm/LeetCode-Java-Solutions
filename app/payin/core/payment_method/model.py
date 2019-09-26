from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel
from typing_extensions import final

from app.commons.utils.types import PaymentProvider
from app.payin.core.exceptions import PayinErrorCode, PaymentMethodReadError
from app.payin.core.payment_method.types import WalletType
from app.payin.core.types import PgpPaymentMethodResourceId
from app.payin.repository.payment_method_repo import (
    PgpPaymentMethodDbEntity,
    StripeCardDbEntity,
)


@final
class Wallet(BaseModel):
    type: WalletType
    dynamic_last4: str


@final
class Card(BaseModel):
    last4: str
    exp_year: str
    exp_month: str
    fingerprint: str
    active: bool
    country: Optional[str]
    brand: Optional[str]
    wallet: Optional[Wallet] = None


@final
class Addresses(BaseModel):
    postal_code: Optional[str] = None


@final
class BillingDetails(BaseModel):
    addresses: Addresses


@final
class PaymentGatewayProviderDetails(BaseModel):
    payment_provider: str
    payment_method_id: Optional[str] = None
    customer_id: Optional[str] = None


@final
class PaymentMethod(BaseModel):
    id: Optional[UUID] = None  # make it optional for existing DSJ stripe_card
    payer_id: Optional[UUID] = None
    type: str
    dd_payer_id: Optional[str] = None
    dd_stripe_card_id: int  # primary key of maindb_stripe_card
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    card: Card
    billing_details: BillingDetails
    payment_gateway_provider_details: PaymentGatewayProviderDetails


@final
class PaymentMethodList(BaseModel):
    count: int
    has_more: bool  # Currently default to False. Returning all the disputes for a query
    data: List[PaymentMethod]


class RawPaymentMethod:
    def __init__(
        self,
        pgp_payment_method_entity: Optional[PgpPaymentMethodDbEntity] = None,
        stripe_card_entity: Optional[StripeCardDbEntity] = None,
    ):
        self.pgp_payment_method_entity = pgp_payment_method_entity
        self.stripe_card_entity = stripe_card_entity

    def to_payment_method(self) -> PaymentMethod:
        """
        Build PaymentMethod object.

        :param pgp_payment_method_entity: pgp_payment_method_entity returned from pgp_payment_method. It could
               be None if the payment_method was not created through payin APIs.
        :param stripe_card_entity:
        :return: PaymentMethod object
        """
        if not self.stripe_card_entity:
            raise PaymentMethodReadError(
                error_code=PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND, retryable=False
            )

        wallet: Optional[Wallet] = None
        if self.stripe_card_entity.tokenization_method:
            wallet = Wallet(
                type=self.stripe_card_entity.tokenization_method,
                dynamic_last4=self.stripe_card_entity.dynamic_last4,
            )

        card: Card = Card(
            country=self.stripe_card_entity.country_of_origin,
            last4=self.stripe_card_entity.last4,
            exp_year=self.stripe_card_entity.exp_year,
            exp_month=self.stripe_card_entity.exp_month,
            fingerprint=self.stripe_card_entity.fingerprint,
            active=self.stripe_card_entity.active,
            brand=self.stripe_card_entity.type,
            wallet=wallet,
        )

        payment_gateway_provider_details: PaymentGatewayProviderDetails = PaymentGatewayProviderDetails(
            payment_provider=(
                self.pgp_payment_method_entity.pgp_code
                if self.pgp_payment_method_entity
                else PaymentProvider.STRIPE
            ),
            payment_method_id=self.stripe_card_entity.stripe_id,
            customer_id=self.stripe_card_entity.external_stripe_customer_id,
        )

        billing_details: BillingDetails = BillingDetails(
            addresses=Addresses(postal_code=self.stripe_card_entity.zip_code)
        )

        return (
            PaymentMethod(
                id=self.pgp_payment_method_entity.id,
                payer_id=self.pgp_payment_method_entity.payer_id,
                dd_payer_id=self.pgp_payment_method_entity.legacy_consumer_id,
                type=self.pgp_payment_method_entity.type,
                dd_stripe_card_id=self.stripe_card_entity.id,
                card=card,
                payment_gateway_provider_details=payment_gateway_provider_details,
                billing_details=billing_details,
                created_at=self.pgp_payment_method_entity.created_at,
                updated_at=self.pgp_payment_method_entity.updated_at,
                deleted_at=self.pgp_payment_method_entity.deleted_at,
            )
            if self.pgp_payment_method_entity
            else PaymentMethod(
                payer_id=None,
                dd_payer_id=str(self.stripe_card_entity.consumer_id),
                type="card",
                dd_stripe_card_id=self.stripe_card_entity.id,
                card=card,
                payment_gateway_provider_details=payment_gateway_provider_details,
                billing_details=billing_details,
                created_at=self.stripe_card_entity.created_at,
                deleted_at=self.stripe_card_entity.removed_at,
                updated_at=None,
            )
        )

    @property
    def pgp_payment_method_resource_id(self) -> PgpPaymentMethodResourceId:
        if self.pgp_payment_method_entity:
            return PgpPaymentMethodResourceId(
                self.pgp_payment_method_entity.pgp_resource_id
            )
        elif self.stripe_card_entity:
            return PgpPaymentMethodResourceId(self.stripe_card_entity.stripe_id)

        raise Exception("RawPaymentMethod doesn't have pgp_payment_method_id")

    def legacy_dd_stripe_card_id(self) -> Optional[str]:
        return str(self.stripe_card_entity.id) if self.stripe_card_entity else None

    def payer_id(self) -> Optional[UUID]:
        return (
            self.pgp_payment_method_entity.payer_id
            if self.pgp_payment_method_entity
            else None
        )
