import datetime
from typing import Optional, List
from src.collectors.interface import CollectorInterface, CollectionResult, CollectItem
from src.data_sources.east_money import fetch_kline


class KlineCollector(CollectorInterface):
    def data_type(self) -> str:
        return "KLINE"

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
                raw = self._fetch_kline(symbol, date_from, date_to)
                item = CollectItem(
                    symbol=symbol,
                    data=raw,
                    collected_at=datetime.datetime.now(),
                )
                result.success_items.append(item)
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

    def _fetch_kline(self, symbol: str, date_from: Optional[str], date_to: Optional[str]) -> list[dict]:
        return fetch_kline(
            symbol,
            date_from=date_from or "20250101",
            date_to=date_to or "20260611",
        )
