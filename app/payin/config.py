import attr
from typing_extensions import Protocol


@attr.s(frozen=True, auto_attribs=True)
class PayinAppConfig(Protocol):

    PAYIN_MAINDB_URL: str
