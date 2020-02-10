from datetime import datetime
from enum import Enum
from typing import Optional

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


# marqeta card fields are not always consistent, we only map the useful ones
class MarqetaProviderCard(BaseModel):
    created_time: datetime
    last_modified_time: datetime
    token: str
    user_token: str
    card_product_token: str
    last_four: str
    state: CardState
    state_reason: Optional[str]


class MarqetaCardAcceptor(BaseModel):
    name: str
    mid: str
    city: str
    state: str
    zip: str


class MarqetaAuthData(BaseModel):
    # minimal info needed from Marqeta auth data to record transaction event
    token: str
    card_token: str
    card_acceptor: MarqetaCardAcceptor
    type: str
    amount: float
