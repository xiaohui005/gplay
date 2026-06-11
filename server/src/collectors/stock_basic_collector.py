import datetime
from typing import Optional, List
from src.collectors.interface import CollectorInterface, CollectionResult, CollectItem
from src.data_sources.east_money import fetch_stock_list


class StockBasicCollector(CollectorInterface):
    def data_type(self) -> str:
        return "STOCK_BASIC"

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

        try:
            raw = self._fetch_all_stocks()
            for item_data in raw:
                result.success_items.append(CollectItem(
                    symbol=item_data.get("symbol", ""),
                    data=item_data,
                    collected_at=datetime.datetime.now(),
                ))
        except Exception as e:
            result.failed_items.append(CollectItem(
                symbol="ALL",
                data={},
                error_code="ERR_FETCH_ALL",
                error_message=str(e),
            ))

        return result

    def _fetch_all_stocks(self) -> List[dict]:
        return fetch_stock_list()
