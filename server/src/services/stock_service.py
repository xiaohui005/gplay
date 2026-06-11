import logging

from src.analysis.engine import AnalysisEngine
from src.repositories.stock_basic_repo import StockBasicRepo
from src.repositories.stock_quote_snapshot_repo import StockQuoteSnapshotRepo

logger = logging.getLogger(__name__)


class StockService:
    def __init__(self, db):
        self.db = db
        self.basic_repo = StockBasicRepo(db)
        self.quote_repo = StockQuoteSnapshotRepo(db)
        self.analysis_engine = AnalysisEngine(db)

    def search(self, keyword: str, limit: int = 20) -> list[dict]:
        items = self.basic_repo.search(keyword, limit)
        symbols = [s.symbol for s in items]
        latest_quotes = {}
        if symbols:
            for q in self.quote_repo.get_latest_batch(symbols):
                latest_quotes[q.symbol] = q
        results = []
        for s in items:
            q = latest_quotes.get(s.symbol)
            results.append({
                "symbol": s.symbol,
                "name": s.name,
                "market": s.market,
                "latestPrice": q.latest_price if q else None,
                "changePercent": q.change_percent if q else None,
                "tradeStatus": s.trade_status,
            })
        return results

    def get_analysis(self, symbol: str, strategy_version: str | None = None) -> dict | None:
        return self.analysis_engine.analyze(symbol, strategy_version)

    def get_quote(self, symbol: str) -> dict | None:
        quote = self.quote_repo.get_latest_by_symbol(symbol)
        if not quote:
            return None
        return quote.to_dict()
