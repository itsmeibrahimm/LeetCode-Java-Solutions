from pydantic import BaseModel


class Acknowledgement(BaseModel):
    acknowledged: bool = True
