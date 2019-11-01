from typing import TypeVar, Optional

T = TypeVar("T")


def self_or_fail_if_none(value: Optional[T]) -> T:
    """
    Return value from Optional wrapped type. Fail with ValueError if is None.
    """
    if value is None:
        raise ValueError("expected value present")
    return value
