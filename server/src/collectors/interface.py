import datetime
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Optional, List


@dataclass
class CollectItem:
    symbol: str
    data: dict
    collected_at: Optional[datetime.datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class CollectionResult:
    data_type: str
    source_code: str
    success_items: List[CollectItem] = field(default_factory=list)
    failed_items: List[CollectItem] = field(default_factory=list)
    is_partial: bool = False


class CollectorInterface(ABC):
    @abstractmethod
    def data_type(self) -> str:
        ...

    @abstractmethod
    def collect(
        self,
        symbols: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> CollectionResult:
        ...
