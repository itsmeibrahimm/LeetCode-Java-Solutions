import pytest
from dataclasses import dataclass
from app.commons.database.model import DBEntity


class TestDBEntity:
    class Model(DBEntity):
        id: int

    class OrmModel(Model):
        class Config:
            orm_mode = True

    @dataclass
    class ObjWithExtras:
        id: int
        other: str

    def test_model(self):
        model = TestDBEntity.Model(id=3)
        assert model.id == 3

        with pytest.raises(TypeError, match=r"immutable"):
            model.id = 6

    def test_model_orm_mode(self):
        """
        validate that you can override orm_mode in a subclass
        """
        obj = TestDBEntity.ObjWithExtras(id=1, other="two")
        model = TestDBEntity.OrmModel.from_orm(obj)
        assert model.id == 1

    def test_model_from_row(self):
        """
        ensure that object creation ignores extra fields from the Record
        """
        row = {"id": 5, "other": "three"}
        model = TestDBEntity.Model.from_row(row)
        assert model.id == 5
