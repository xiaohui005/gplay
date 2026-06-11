from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.models.stock_basic import StockBasic


class StockBasicRepo:
    def __init__(self, db: Session):
        self.db = db

    def search(self, keyword: str, limit: int = 20) -> list[StockBasic]:
        if not keyword:
            return []
        term = f"%{keyword}%"
        q = self.db.query(StockBasic).filter(
            or_(
                StockBasic.symbol.startswith(keyword),
                StockBasic.name.like(term),
                StockBasic.pinyin.like(term),
            )
        )
        return q.limit(limit).all()

    def get_by_symbol(self, symbol: str) -> StockBasic | None:
        return self.db.query(StockBasic).filter(StockBasic.symbol == symbol).first()

    def upsert(self, record: StockBasic) -> StockBasic:
        existing = self.get_by_symbol(record.symbol)
        if existing:
            for key, val in record.to_dict().items():
                if val is not None and key not in ("symbol",):
                    col = getattr(StockBasic, key, None)
                    if col is not None:
                        setattr(existing, key, val)
            existing.update_time = record.update_time
            self.db.flush()
            return existing
        self.db.add(record)
        self.db.flush()
        return record

    def bulk_upsert(self, records: list[StockBasic]):
        for r in records:
            self.upsert(r)
