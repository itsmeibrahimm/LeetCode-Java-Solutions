from typing import Optional

from pydantic import BaseModel


class ExampleStatus(BaseModel):
    status: int
    message: str
    retryable: Optional[bool]
