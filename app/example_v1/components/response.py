from typing import Generic, Optional, TypeVar

from pydantic.generics import GenericModel

from app.example_v1.components.status import ExampleStatus


DataT = TypeVar("DataT")


class ExampleResponse(GenericModel, Generic[DataT]):
    status: ExampleStatus
    error: Optional[str]
    result: Optional[DataT]
