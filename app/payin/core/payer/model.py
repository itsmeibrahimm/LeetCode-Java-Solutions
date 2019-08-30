from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel
from typing_extensions import final

from app.commons.utils.types import PaymentProvider
from app.payin.repository.payer_repo import (
    PayerDbEntity,
    PgpCustomerDbEntity,
    StripeCustomerDbEntity,
)


class PaymentGatewayProviderCustomer(BaseModel):
    payment_provider: str
    payment_provider_customer_id: str
    default_payment_method_id: Optional[str] = None


# https://pydantic-docs.helpmanual.io/#self-referencing-models
PaymentGatewayProviderCustomer.update_forward_refs()


@final
class Payer(BaseModel):
    id: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime] = None
    payer_type: Optional[str] = None
    country: Optional[str] = None
    dd_payer_id: Optional[str] = None
    description: Optional[str] = None
    payment_gateway_provider_customers: Optional[
        List[PaymentGatewayProviderCustomer]
    ] = None


@final
@dataclass(frozen=True)
class PgpCustomer:
    id: str
    legacy_id: int
    pgp_code: str
    pgp_resource_id: str
    payer_id: str
    created_at: datetime
    updated_at: datetime
    account_balance: Optional[int] = None
    currency: Optional[str] = None
    default_payment_method_id: Optional[str] = None
    legacy_default_card_id: Optional[str] = None
    legacy_default_source_id: Optional[str] = None


@final
@dataclass(frozen=True)
class StripeCustomer:
    id: int
    stripe_id: str
    country_shortname: str
    owner_type: str
    owner_id: int
    default_card: str
    default_source: str


class RawPayer:
    def __init__(
        self,
        payer_entity: Optional[PayerDbEntity] = None,
        pgp_customer_entity: Optional[PgpCustomerDbEntity] = None,
        stripe_customer_entity: Optional[StripeCustomerDbEntity] = None,
    ):
        self.payer_entity = payer_entity
        self.pgp_customer_entity = pgp_customer_entity
        self.stripe_customer_entity = stripe_customer_entity

    def country(self):
        country: str
        if self.payer_entity:
            country = self.payer_entity.country
        elif self.stripe_customer_entity:
            country = self.stripe_customer_entity.country_shortname
        return country

    def pgp_customer_id(self):
        if self.payer_entity:
            pgp_customer_id = self.payer_entity.legacy_stripe_customer_id
        elif self.pgp_customer_entity:
            pgp_customer_id = self.pgp_customer_entity.pgp_resource_id
        elif self.stripe_customer_entity:
            pgp_customer_id = self.stripe_customer_entity.stripe_id
        return pgp_customer_id

    def to_payer(self):
        """
        Build Payer object.

        :param payer_entity:
        :param pgp_customer_entity:
        :param stripe_customer_entity:
        :return: Payer object
        """
        payer: Payer
        provider_customer: PaymentGatewayProviderCustomer
        if self.payer_entity:
            if self.pgp_customer_entity:
                provider_customer = PaymentGatewayProviderCustomer(
                    payment_provider=self.pgp_customer_entity.pgp_code,
                    payment_provider_customer_id=self.pgp_customer_entity.pgp_resource_id,
                    default_payment_method_id=self.pgp_customer_entity.default_payment_method_id,
                )
            else:
                provider_customer = PaymentGatewayProviderCustomer(
                    payment_provider=PaymentProvider.STRIPE.value,  # hard-coded "stripe"
                    payment_provider_customer_id=self.payer_entity.legacy_stripe_customer_id,
                )
            payer = Payer(
                id=self.payer_entity.id,
                payer_type=self.payer_entity.payer_type,
                payment_gateway_provider_customers=[provider_customer],
                country=self.payer_entity.country,
                dd_payer_id=self.payer_entity.dd_payer_id,
                description=self.payer_entity.description,
                created_at=self.payer_entity.created_at,
                updated_at=self.payer_entity.updated_at,
            )
        elif self.stripe_customer_entity:
            provider_customer = PaymentGatewayProviderCustomer(
                payment_provider=PaymentProvider.STRIPE.value,  # hard-coded "stripe"
                payment_provider_customer_id=self.stripe_customer_entity.stripe_id,
                default_payment_method_id=self.stripe_customer_entity.default_card,
            )
            if self.payer_entity:
                payer = Payer(
                    id=self.payer_entity.id,
                    payer_type=self.payer_entity.payer_type,
                    payment_gateway_provider_customers=[provider_customer],
                    country=self.payer_entity.country,
                    dd_payer_id=self.payer_entity.dd_payer_id,
                    description=self.payer_entity.description,
                    created_at=self.payer_entity.created_at,
                    updated_at=self.payer_entity.updated_at,
                )
            else:
                payer = Payer(
                    id=self.stripe_customer_entity.stripe_id,  # FIXME: ensure payer lazy creation
                    created_at=datetime.utcnow(),  # FIXME: ensure payer lazy creation
                    updated_at=datetime.utcnow(),  # FIXME: ensure payer lazy creation
                    country=self.stripe_customer_entity.country_shortname,
                    dd_payer_id=str(self.stripe_customer_entity.owner_id),
                    # payer_type=stripe_customer_entity.owner_type,
                    payment_gateway_provider_customers=[provider_customer],
                )

        return payer
