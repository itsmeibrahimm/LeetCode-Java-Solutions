from typing import List

import attr
from gino import Gino
from sqlalchemy import Column, Table


@attr.s(frozen=True, auto_attribs=True)
class TableDefinition:
    """
    Customized wrapper around SqlAlchemy Table object so that we can statically refer to column names and add more
    extensions around table schema
    """

    gino: Gino
    table: Table = attr.ib(init=False)
    name: str = attr.ib(init=False)

    def __attrs_post_init__(self):
        """
        Utilize attrs post init hook to load any instance attribute
        with sqlalchemy.Column type as a column of delegate Table
        """
        columns: List[Column] = []
        for k in dir(self):
            attribute = self.__getattribute__(k)
            if isinstance(attribute, Column):
                columns.append(attribute)
        object.__setattr__(self, "table", Table(self.name, self.gino, *columns))
