import pytest

from app.commons.utils import validation
from app.commons.utils.validation import count_present


def test_not_none():
    with pytest.raises(ValueError):
        validation.not_none(None)

    with pytest.raises(ValueError) as exc_info:
        validation.not_none(None, "expected")
    error: ValueError = exc_info.value
    assert error.args[0] == "expected"

    value = "non-None"
    assert value is validation.not_none(value)

    empty_str = ""
    assert empty_str is validation.not_none(empty_str)

    empty_list = []
    assert empty_list is validation.not_none(empty_list)

    empty_tuple = ()
    assert empty_tuple is validation.not_none(empty_tuple)

    empty_dict = {}
    assert empty_dict is validation.not_none(empty_dict)

    zero = 0
    assert zero is validation.not_none(zero)


def test_count_present():
    assert count_present() == 0
    assert count_present(None) == 0
    assert count_present(None, None, None) == 0
    assert count_present(1, "abc", ["abc", 1], None, 123) == 4
    assert count_present(["123", 1]) == 1
    assert count_present("something") == 1
