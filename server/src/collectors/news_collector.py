import datetime
from typing import Optional, List
from src.collectors.interface import CollectorInterface, CollectionResult, CollectItem
from src.data_sources.east_money_news import fetch_news


class NewsCollector(CollectorInterface):
    def data_type(self) -> str:
        return "NEWS"

    def collect(
        self,
        symbols: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> CollectionResult:
        result = CollectionResult(
            data_type=self.data_type(),
            source_code="east_money_free",
        )

        if not symbols:
            result.failed_items.append(CollectItem(
                symbol="",
                data={},
                error_code="ERR_NO_SYMBOLS",
                error_message="未指定股票代码列表",
            ))
            return result

        for symbol in symbols:
            try:
                items = self._fetch_news(symbol)
                for item in items:
                    result.success_items.append(CollectItem(
                        symbol=symbol,
                        data=item,
                        collected_at=datetime.datetime.now(),
                    ))
            except Exception as e:
                result.failed_items.append(CollectItem(
                    symbol=symbol,
                    data={},
                    error_code="ERR_FETCH",
                    error_message=str(e),
                ))

        if result.failed_items and result.success_items:
            result.is_partial = True
        return result

    def _fetch_news(self, symbol: str) -> list[dict]:
        return fetch_news(symbol, count=20)
