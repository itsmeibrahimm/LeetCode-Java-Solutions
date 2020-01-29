from typing import TypeVar, Optional

T = TypeVar("T")


def not_none(value: Optional[T], err_msg: Optional[str] = None) -> T:
    """
    Return value from Optional wrapped type. Fail with ValueError if is None.
    """
    if value is None:
        msg = err_msg or "expected value present"
        raise ValueError(msg)
    return value


def count_present(*items) -> int:
    """

    Args:
        *items (): a list of any objects including None

    Returns: number of items provided that are not strict None

    """
    return len([item for item in items if item is not None])
