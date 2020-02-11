from datetime import datetime
from pydantic import BaseModel


class InternalStoreCardPaymentMetadata(BaseModel):
    updated_at: datetime
