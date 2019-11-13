from typing import List
from unittest.mock import MagicMock, create_autospec

import pytest
from pydantic import BaseModel, PositiveInt, ValidationError

from app.commons.api.exceptions import _build_request_validation_error_display


class TestRequestValidationExceptionMessage:
    class Model(BaseModel):
        positive_int: PositiveInt
        str_list: List[str]

    def test_one_validation_error(self):
        with pytest.raises(ValidationError) as e:
            TestRequestValidationExceptionMessage.Model(
                positive_int=0, str_list=["something"]
            )  # type: ignore

        error = e.value
        assert isinstance(error, ValidationError)
        assert len(error.errors()) == 1
        message = _build_request_validation_error_display(error)
        assert message, "expected non-empty message"

    def test_mutiple_validation_error(self):
        with pytest.raises(ValidationError) as e:
            TestRequestValidationExceptionMessage.Model(
                positive_int=0, str_list={"a": 123}
            )  # type: ignore

        error = e.value
        assert isinstance(error, ValidationError)
        assert len(error.errors()) == 2
        message = _build_request_validation_error_display(error)
        assert message, "expected non-empty message"

    def test_malformed_exception(self):
        exception: ValidationError = create_autospec(ValidationError)
        exception.errors.return_value = [{"bad_loc": ["something"], "bad_msg": "bla"}]
        exception.model.__name__ = MagicMock()
        message = _build_request_validation_error_display(exception)
        assert message, "expected non-empty message"
