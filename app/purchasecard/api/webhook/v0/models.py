from typing import Optional, List
from pydantic import BaseModel
from app.purchasecard.core.webhook.models import Transaction
from app.commons.api.models import PaymentResponse


class MarqetaWebhookRequest(BaseModel):
    transactions: Optional[List[Transaction]]


class WebhookResponse(PaymentResponse):
    ...
