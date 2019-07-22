from copy import deepcopy
from typing import TypeVar

import attr

T = TypeVar("T")


def no_init_attrib(val: T = None) -> T:
    """
    A short cut on attrs to declare an instance variable which should only be initialized internally
    not through direct assignment in __init__
    :param val: attribute's val
    """
    return (
        attr.ib(init=False)
        if val is None
        else attr.ib(init=False, factory=lambda: deepcopy(val))
    )
