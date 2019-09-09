from typing import Optional

from pydantic import BaseModel


class Acknowledgement(BaseModel):
    affected_record_count: Optional[int]
    acknowledged: bool = True
