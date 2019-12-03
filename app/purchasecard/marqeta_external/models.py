from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class CardState(str, Enum):
    UNACTIVATED = "UNACTIVATED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    UNSUPPORTED = "UNSUPPORTED"


class FulfillmentStatus(str, Enum):
    ISSUED = "ISSUED"
    ORDERED = "ORDERED"
    REORDERED = "REORDERED"
    REJECTED = "REJECTED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    DIGITALLY_PRESENTED = "DIGITALLY_PRESENTED"


class MarqetaProviderCreateUserRequest(BaseModel):
    token: str
    first_name: str
    last_name: str
    email: str


class MarqetaProviderCreateUserResponse(BaseModel):
    token: str


class MarqetaProviderGetCardRequest(BaseModel):
    token: str
    last4: str


class MarqetaProviderCard(BaseModel):
    created_time: datetime
    last_modified_time: datetime
    token: str
    user_token: str
    card_product_token: str
    last_four: str
    pan: str
    expiration: str
    expiration_time: datetime
    barcode: str
    pin_is_set: bool
    state: CardState
    state_reason: str
    fulfillment_status: FulfillmentStatus
    instrument_type: str
    expedite: bool
