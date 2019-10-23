from pydantic import BaseModel


class InternalMarqetaUser(BaseModel):
    token: str
