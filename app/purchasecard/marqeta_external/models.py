from pydantic import BaseModel


class MarqetaProviderCreateUserRequest(BaseModel):
    token: str
    first_name: str
    last_name: str
    email: str


class MarqetaProviderCreateUserResponse(BaseModel):
    token: str
