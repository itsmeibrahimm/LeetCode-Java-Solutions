from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class Cacheable(ABC):
    @classmethod
    @abstractmethod
    def serialize(cls, data) -> str:
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, cached_data: str) -> Optional[BaseModel]:
        pass


class CacheKeyAware(ABC):
    @abstractmethod
    def get_cache_key(self) -> dict:
        pass
