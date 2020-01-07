from pydantic import BaseModel


class InternalStoreCardPaymentMetadata(BaseModel):
    updated_at: str
