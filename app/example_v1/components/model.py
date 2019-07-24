from __future__ import annotations
from typing import Any, List, Optional
from uuid import UUID

import datetime as dt

from pydantic import BaseModel

from app.example_v1.components.enum import ExampleEnum


class ExampleModel(BaseModel):
    string: str
    number: int
    floating: float
    uuid: UUID
    date: dt.date
    datetime: dt.datetime
    optional: Optional[str] = None
    array: List[Any]
    enum: ExampleEnum = ExampleEnum.FOO
    nested: Optional[ExampleModel]


# https://pydantic-docs.helpmanual.io/#self-referencing-models
ExampleModel.update_forward_refs()
