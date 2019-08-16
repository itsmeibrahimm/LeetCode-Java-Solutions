from pydantic import BaseModel


class VerifyTokenResponse(BaseModel):
    """
    Adapter model to limit future code changes when we migrate to grpc for identity
    """

    client_id: int
    client_name: str
    service_id: int
    service_name: str
    from_cache: bool = False
