from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel
from typing_extensions import final

from app.commons.types import PgpCode
from app.commons.utils.legacy_utils import owner_type_to_payer_reference_id_type
from app.payin.core.types import PgpPayerResourceId, PayerReferenceIdType
from app.payin.repository.payer_repo import (
    PayerDbEntity,
    PgpCustomerDbEntity,
    StripeCustomerDbEntity,
)


class PaymentGatewayProviderCustomer(BaseModel):
    payment_provider: PgpCode
    payment_provider_customer_id: str
    default_payment_method_id: Optional[str] = None


class PayerCorrelationIds(BaseModel):
    payer_reference_id: str
    payer_reference_id_type: PayerReferenceIdType


@final
class Payer(BaseModel):
    id: Optional[UUID] = None  # make it optional for existing DSJ consumer
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime] = None
    country: Optional[str] = None
    payer_correlation_ids: Optional[PayerCorrelationIds] = None
    dd_stripe_customer_id: Optional[str] = None
    default_payment_method_id: Optional[UUID] = None
    default_dd_stripe_card_id: Optional[int] = None
    description: Optional[str] = None
    payment_gateway_provider_customers: Optional[
        List[PaymentGatewayProviderCustomer]
    ] = None


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

    # FIXME: change to @property, and throw exception if not found
    def country(self) -> Optional[str]:
        country: Optional[str] = None
        if self.payer_entity:
            country = self.payer_entity.country
        elif self.stripe_customer_entity:
            country = self.stripe_customer_entity.country_shortname
        return country

    @property
    def pgp_payer_resource_id(self) -> PgpPayerResourceId:
        if self.payer_entity:
            assert self.payer_entity.legacy_stripe_customer_id
            return PgpPayerResourceId(self.payer_entity.legacy_stripe_customer_id)
        elif self.pgp_customer_entity:
            return PgpPayerResourceId(self.pgp_customer_entity.pgp_resource_id)
        elif self.stripe_customer_entity:
            return PgpPayerResourceId(self.stripe_customer_entity.stripe_id)

        raise Exception("RawPayer doesn't have pgp_customer_id")

    def pgp_default_payment_method_id(self) -> Optional[str]:
        default_payment_method_id: Optional[str] = None
        if self.pgp_customer_entity:
            # Stripe specific rule: default_payment_method_id has higher priority than default_source_id
            # TODOs: update doc link for testing result for reference.
            if self.pgp_customer_entity.default_payment_method_id:
                default_payment_method_id = (
                    self.pgp_customer_entity.default_payment_method_id
                )
            else:
                default_payment_method_id = (
                    self.pgp_customer_entity.legacy_default_source_id
                )
        elif self.stripe_customer_entity:
            default_payment_method_id = self.stripe_customer_entity.default_source
        return default_payment_method_id

    def to_payer(self):
        """
        Build Payer object.

        :return: Payer object
        """

        payer: Payer
        provider_customer: PaymentGatewayProviderCustomer

        if self.payer_entity:
            updated_at: datetime = self.payer_entity.updated_at
            dd_stripe_customer_id: Optional[str] = None
            if (
                self.payer_entity.payer_reference_id_type
                == PayerReferenceIdType.DD_CONSUMER_ID
            ):
                if self.pgp_customer_entity:
                    updated_at = max(
                        self.pgp_customer_entity.updated_at,
                        self.payer_entity.updated_at,
                    )
                    provider_customer = PaymentGatewayProviderCustomer(
                        payment_provider=self.pgp_customer_entity.pgp_code,
                        payment_provider_customer_id=self.pgp_customer_entity.pgp_resource_id,
                        default_payment_method_id=self.pgp_default_payment_method_id(),
                    )
            else:
                if not self.stripe_customer_entity:
                    raise Exception("RawPayer doesn't have stripe_customer_entity")
                dd_stripe_customer_id = str(self.stripe_customer_entity.id)
                provider_customer = PaymentGatewayProviderCustomer(
                    payment_provider=PgpCode.STRIPE,
                    payment_provider_customer_id=self.payer_entity.legacy_stripe_customer_id,
                    default_payment_method_id=(
                        self.stripe_customer_entity.default_source
                    ),
                )
            payer = Payer(
                id=self.payer_entity.id,
                payment_gateway_provider_customers=[provider_customer],
                country=self.payer_entity.country,
                payer_correlation_ids=PayerCorrelationIds(
                    payer_reference_id=self.payer_entity.payer_reference_id,
                    payer_reference_id_type=self.payer_entity.payer_reference_id_type,
                ),
                dd_stripe_customer_id=dd_stripe_customer_id,
                default_payment_method_id=self.payer_entity.default_payment_method_id,
                default_dd_stripe_card_id=self.payer_entity.legacy_default_dd_stripe_card_id,
                description=self.payer_entity.description,
                created_at=self.payer_entity.created_at,
                updated_at=updated_at,
            )
        elif self.stripe_customer_entity:
            provider_customer = PaymentGatewayProviderCustomer(
                payment_provider=PgpCode.STRIPE,
                payment_provider_customer_id=self.stripe_customer_entity.stripe_id,
                default_payment_method_id=(self.stripe_customer_entity.default_source),
            )
            payer = Payer(
                # created_at=datetime.utcnow(),  # FIXME: ensure payer lazy creation
                # updated_at=datetime.utcnow(),  # FIXME: ensure payer lazy creation
                country=self.stripe_customer_entity.country_shortname,
                dd_stripe_customer_id=str(self.stripe_customer_entity.id),
                payer_correlation_ids=PayerCorrelationIds(
                    payer_reference_id=str(self.stripe_customer_entity.owner_id),
                    payer_reference_id_type=owner_type_to_payer_reference_id_type(
                        owner_type=self.stripe_customer_entity.owner_type
                    ),
                ),
                payment_gateway_provider_customers=[provider_customer],
            )

        return payer
