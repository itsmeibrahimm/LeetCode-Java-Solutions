from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.commons.api.models import PaymentResponse


class RecordTransactionEventsRequest(BaseModel):
    marqeta_user_token: str
    anchor_day: datetime
    shift_id: str


class TransactionEvent(PaymentResponse):
    created_at: datetime
    token: str
    amount: int
    transaction_type: str
    shift_id: str
    card_acceptor_name: Optional[str] = None
    card_inactive: bool
    insufficient_funds: bool
    is_unsuccessful_payment: bool
    raw_type: str
    available_balance: float
