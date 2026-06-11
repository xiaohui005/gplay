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

    def get_kline(self, symbol: str, days: int = 60) -> list[dict]:
        from src.models.stock_kline_daily import StockKlineDaily
        import datetime
        cutoff = datetime.date.today() - datetime.timedelta(days=days)
        rows = (
            self.db.query(StockKlineDaily)
            .filter(StockKlineDaily.symbol == symbol, StockKlineDaily.trade_date >= cutoff.isoformat())
            .order_by(StockKlineDaily.trade_date.asc())
            .all()
        )
        return [r.to_dict() for r in rows]

    def get_news(self, symbol: str, limit: int = 20) -> list[dict]:
        from src.models.stock_news import StockNews
        rows = (
            self.db.query(StockNews)
            .filter(StockNews.symbol == symbol)
            .order_by(StockNews.publish_time.desc().nullslast())
            .limit(limit)
            .all()
        )
        return [r.to_dict() for r in rows]
