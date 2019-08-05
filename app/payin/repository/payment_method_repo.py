from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any

from typing_extensions import final

from app.commons.database.model import DBEntity


###########################################################
# PgpPaymentMethod DBEntity and CRUD operations           #
###########################################################
from app.payin.repository.base import PayinDBRepository


class PgpPeymentMethodDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: str
    pgp_code: str
    pgp_resource_id: str
    payer_id: Optional[str] = None
    pgp_card_id: Optional[str] = None
    legacy_stripe_card_serial_id: Optional[int] = None
    legacy_consumer_id: Optional[str] = None
    object: Optional[str] = None
    type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    attached_at: Optional[datetime] = None
    detached_at: Optional[datetime] = None


###########################################################
# StripeCard DBEntity and CRUD operations                 #
###########################################################
class StripeCardDbEntity(DBEntity):
    """
    The variable name must be consistent with DB table column name
    """

    id: int
    stripe_id: str
    fingerprint: str
    last4: str
    dynamic_last4: str
    exp_month: str
    exp_year: str
    type: str
    country_of_origin: Optional[str]
    zip_code: Optional[str]
    created_at: Optional[datetime] = None
    removed_at: Optional[datetime] = None
    is_scanned: Optional[bool]
    dd_fingerprint: Optional[str]
    active: bool
    consumer_id: Optional[int]
    stripe_customer_id: Optional[int]
    external_stripe_customer_id: Optional[str]
    tokenization_method: Optional[str]
    address_line1_check: Optional[str]
    address_zip_check: Optional[str]
    validation_card_id: Optional[int]


class PaymentMethodRepositoryInterface:
    @abstractmethod
    async def insert_payment_method_and_stripe_card(self, request: Any) -> Any:
        ...


@final
@dataclass
class PaymentMethodRepository(PaymentMethodRepositoryInterface, PayinDBRepository):
    async def insert_payment_method_and_stripe_card(self, request: Any) -> Any:
        ...
