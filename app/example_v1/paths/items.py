from datetime import date, datetime
from uuid import uuid4

from fastapi import APIRouter

from app.example_v1.components.enum import ExampleEnum
from app.example_v1.components.model import ExampleModel
from app.example_v1.components.response import ExampleResponse
from app.example_v1.components.status import ExampleStatus

router = APIRouter()


@router.post("/items", response_model=ExampleResponse[int])
async def create_item(item: ExampleModel) -> ExampleResponse[int]:
    result = 123

    status = ExampleStatus(status=200, code="OK")

    resp = ExampleResponse[int](status=status, result=result)

    return resp


@router.get("/items/{itemId}", response_model=ExampleResponse[ExampleModel])
async def get_item(itemId: int) -> ExampleResponse[ExampleModel]:
    result = ExampleModel(
        string="example string",
        number=10,
        floating=3.14,
        uuid=uuid4(),
        date=date.today(),
        datetime=datetime.now(),
        array=[],
        enum=ExampleEnum.BAR,
        # nested=None,
    )

    status = ExampleStatus(status=200, message="OK")

    resp = ExampleResponse[ExampleModel](status=status, result=result)

    return resp


@router.delete("/items/{itemId}", response_model=ExampleResponse[bool])
async def delete_item(itemId: int) -> ExampleResponse[bool]:
    result = False

    status = ExampleStatus(status=404, code="Not Found", retryable=False)

    resp = ExampleResponse[bool](status=status, result=result)

    return resp
