import attr
from gino import Gino


@attr.s(auto_attribs=True)
class PayinRepositories:
    _maindb_connection: Gino
