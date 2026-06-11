from typing import Optional, List
from src.collectors.interface import CollectorInterface


class CollectorRegistry:
    _collectors: dict[str, type[CollectorInterface]] = {}

    @classmethod
    def register(cls, collector_cls: type[CollectorInterface]):
        instance = collector_cls()
        data_type = instance.data_type()
        cls._collectors[data_type] = collector_cls

    @classmethod
    def get(cls, data_type: str) -> Optional[type[CollectorInterface]]:
        return cls._collectors.get(data_type)

    @classmethod
    def list_types(cls) -> List[str]:
        return list(cls._collectors.keys())

    @classmethod
    def new_instance(cls, data_type: str) -> Optional[CollectorInterface]:
        collector_cls = cls.get(data_type)
        if collector_cls:
            return collector_cls()
        return None
