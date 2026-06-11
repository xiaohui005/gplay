import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.stock_quote_snapshot import StockQuoteSnapshot


class StockQuoteSnapshotRepo:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_by_symbol(self, symbol: str) -> StockQuoteSnapshot | None:
        return (
            self.db.query(StockQuoteSnapshot)
            .filter(StockQuoteSnapshot.symbol == symbol)
            .order_by(StockQuoteSnapshot.data_time.desc())
            .first()
        )

    def get_latest_batch(self, symbols: list[str] | None = None) -> list[StockQuoteSnapshot]:
        sub = (
            self.db.query(
                StockQuoteSnapshot.symbol,
                func.max(StockQuoteSnapshot.data_time).label("max_t"),
            )
            .group_by(StockQuoteSnapshot.symbol)
            .subquery()
        )
        q = self.db.query(StockQuoteSnapshot).join(
            sub,
            (StockQuoteSnapshot.symbol == sub.c.symbol)
            & (StockQuoteSnapshot.data_time == sub.c.max_t),
        )
        if symbols:
            q = q.filter(StockQuoteSnapshot.symbol.in_(symbols))
        return q.all()

    def add(self, record: StockQuoteSnapshot) -> StockQuoteSnapshot:
        self.db.add(record)
        self.db.flush()
        return record

    def bulk_add(self, records: list[StockQuoteSnapshot]):
        for r in records:
            self.db.add(r)
        self.db.flush()
