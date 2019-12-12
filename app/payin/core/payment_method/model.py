from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel
from typing_extensions import final

from app.commons.types import PgpCode
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
    payment_provider: PgpCode
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
    has_more: bool  # Currently default to False. Returning all the payment methods for a query
    data: List[PaymentMethod]


class PaymentMethodIds(BaseModel):
    pgp_payment_method_resource_id: PgpPaymentMethodResourceId
    dd_stripe_card_id: int
    payment_method_id: Optional[
        UUID
    ]  # Optional for existing objects without backfilled yet


class RawPaymentMethod:
    def __init__(
        self,
        stripe_card_entity: StripeCardDbEntity,
        pgp_payment_method_entity: Optional[PgpPaymentMethodDbEntity] = None,
    ):
        self.stripe_card_entity = stripe_card_entity
        self.pgp_payment_method_entity = pgp_payment_method_entity

    def to_payment_method(self) -> PaymentMethod:
        """
        Build PaymentMethod object.
        """

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
                else PgpCode.STRIPE
            ),
            payment_method_id=self.stripe_card_entity.stripe_id,
            customer_id=self.stripe_card_entity.external_stripe_customer_id,
        )

        billing_details: BillingDetails = BillingDetails(
            addresses=Addresses(postal_code=self.stripe_card_entity.zip_code)
        )

        return (
            PaymentMethod(
                id=self.payment_method_id,
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

        return PgpPaymentMethodResourceId(self.stripe_card_entity.stripe_id)

    @property
    def legacy_dd_stripe_card_id(self) -> int:
        return self.stripe_card_entity.id

    @property
    def payment_method_id(self) -> Optional[UUID]:
        return (
            self.pgp_payment_method_entity.payment_method_id
            if self.pgp_payment_method_entity
            else None
        )

    def payer_id(self) -> Optional[UUID]:
        return (
            self.pgp_payment_method_entity.payer_id
            if self.pgp_payment_method_entity
            else None
        )
