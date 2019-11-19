from typing import Dict, Any, Optional, List

from pydantic import BaseModel

from app.commons.api.models import PaymentResponse


class MarqetaWebhookRequest(BaseModel):
    transactions: Optional[List[Dict[str, Any]]]


class WebhookResponse(PaymentResponse):
    ...
