from typing import List
from sqlalchemy.orm import Session
from src.models.raw_market_data import RawMarketData


class RawMarketDataRepo:
    def __init__(self, db: Session):
        self.db = db

    def create(self, raw: RawMarketData) -> RawMarketData:
        self.db.add(raw)
        self.db.commit()
        self.db.refresh(raw)
        return raw

    def batch_create(self, records: List[RawMarketData]):
        self.db.add_all(records)
        self.db.commit()

    def list_by_batch(
        self, batch_id: str, limit: int = 100, offset: int = 0
    ) -> List[RawMarketData]:
        return self.db.query(RawMarketData).filter(
            RawMarketData.batch_id == batch_id
        ).order_by(RawMarketData.created_at.desc()).offset(offset).limit(limit).all()
