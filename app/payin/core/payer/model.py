from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel
from typing_extensions import final

from app.payin.core.payer.types import PayerType


class PaymentGatewayProviderCustomer(BaseModel):
    payment_provider: str
    payment_provider_customer_id: str


# https://pydantic-docs.helpmanual.io/#self-referencing-models
PaymentGatewayProviderCustomer.update_forward_refs()


@final
@dataclass(frozen=True)
class Payer:
    payer_id: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime] = None
    payer_type: Optional[PayerType] = None
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
