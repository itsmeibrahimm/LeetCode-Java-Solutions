from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic.dataclasses import dataclass


# todo: this needs to be moved to commons/types.py
from app.payout.types import AccountType


class PaymentProvider(str, Enum):
    """
    Enum definition of supported payment gateway providers.
    """

    STRIPE = "stripe"


@dataclass
class Nullable:
    pass


@dataclass
class NullableString(Nullable):
    """
    Customized optional string type to differentiate pydantic default None type.
    """

    value: Optional[str] = None


@dataclass
class NullableAccount(Nullable):
    """
    Customized optional AccountType for payment account to differentiate pydantic default None type.
    """

    value: Optional[AccountType] = None


@dataclass
class NullableInteger(Nullable):
    """
    Customized optional int type to differentiate pydantic default None type.
    """

    value: Optional[int] = None


@dataclass
class NullableBoolean(Nullable):
    """
    Customized optional bool type to differentiate pydantic default None type.
    """

    value: Optional[bool] = None


@dataclass
class NullableDatetime(Nullable):
    """
    Customized optional Datetime type to differentiate pydantic default None type.
    """

    value: Optional[datetime] = None


@dataclass
class NullableList(Nullable):
    """
    Customized optional List type to differentiate pydantic default None type.
    """

    value: Optional[list] = None
