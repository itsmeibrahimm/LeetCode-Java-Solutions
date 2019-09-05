import pytest
import json
from dataclasses import dataclass
from pydantic import Json
from typing import Optional
from app.commons.database.model import DBEntity


class TestDBEntity:
    class Model(DBEntity):
        id: int
        json_obj: Optional[Json]

        def _fields_need_json_to_string_conversion(self):
            return ["json_obj"]

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
        assert model.dict(skip_defaults=True) == {"id": 5}

    def test_model_dict_after_json_to_string(self):
        """
        ensure that object creation ignores extra fields from the Record
        """
        model = TestDBEntity.Model(id=5, json_obj=json.dumps({"a": "b"}))
        dict_after_conversion = model.dict_after_json_to_string()
        assert dict_after_conversion.get("id") == 5
        assert dict_after_conversion.get("json_obj") == json.dumps({"a": "b"})
