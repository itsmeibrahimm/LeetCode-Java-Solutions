from pydantic import BaseModel


class HttpResponseBlob(BaseModel):
    error_code: str
    error_message: str
