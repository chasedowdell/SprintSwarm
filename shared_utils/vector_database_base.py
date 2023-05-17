from abc import ABC, abstractmethod
from typing import List
from shared_utils.models import BacklogItem


class VectorDatabaseBase(ABC):
    _instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @abstractmethod
    def add_backlog_item(self, item: BacklogItem, vector: List[float], namespace: str) -> None:
        pass

    def add_code(self, code_base_func: dict) -> None:
        pass

    @abstractmethod
    def delete(self, vector_ids: List[str]) -> None:
        pass

    @abstractmethod
    def search(self, query_vector: List[float],
               num_relevant: int = 5,
               namespace: str = None):
        pass
