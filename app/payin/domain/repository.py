from dataclasses import dataclass

from gino import Gino


@dataclass
class PayinRepositories:
    _maindb_connection: Gino
