import datetime
import random
from typing import Optional, List
from src.collectors.interface import CollectorInterface, CollectionResult, CollectItem


class MockCollector(CollectorInterface):
    def data_type(self) -> str:
        return "MOCK"

    def collect(
        self,
        symbols: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> CollectionResult:
        test_symbols = symbols or ["600000", "000001", "300750"]
        result = CollectionResult(
            data_type=self.data_type(),
            source_code="mock_source",
        )

        for symbol in test_symbols:
            if symbol == "FAIL_SYMBOL":
                result.failed_items.append(CollectItem(
                    symbol=symbol,
                    data={},
                    error_code="ERR_MOCK",
                    error_message="模拟采集失败",
                ))
                continue

            result.success_items.append(CollectItem(
                symbol=symbol,
                data={
                    "symbol": symbol,
                    "name": f"测试股票{symbol}",
                    "latestPrice": round(random.uniform(5, 100), 2),
                    "changePercent": round(random.uniform(-10, 10), 2),
                    "volume": random.randint(100000, 10000000),
                    "amount": round(random.uniform(1000000, 1000000000), 2),
                },
                collected_at=datetime.datetime.now(),
            ))

        if result.failed_items:
            result.is_partial = True

        return result
