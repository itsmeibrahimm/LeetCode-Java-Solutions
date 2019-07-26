from copy import deepcopy
from dataclasses import field
from typing import TypeVar

T = TypeVar("T")


def no_init_field(val: T = None) -> T:
    """
    A short cut on dataclass:field to declare an instance variable which should only be initialized internally
    not through direct assignment in __init__
    :param val: attribute's fixed value

    Note: we use default_factory with deepcopy(val) here instead of default=val, since default val will be stored
    at class level which make all instances of the class sharing exact same instance of a default value.
    """
    return (
        field(init=False)
        if val is None
        else field(init=False, default_factory=lambda: deepcopy(val))
    )
