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
