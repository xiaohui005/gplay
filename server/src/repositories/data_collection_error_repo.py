from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models.data_collection_error import DataCollectionError


class DataCollectionErrorRepo:
    def __init__(self, db: Session):
        self.db = db

    def create(self, error: DataCollectionError) -> DataCollectionError:
        self.db.add(error)
        self.db.commit()
        self.db.refresh(error)
        return error

    def batch_create(self, errors: List[DataCollectionError]):
        self.db.add_all(errors)
        self.db.commit()

    def list_by_batch(
        self, batch_id: str, limit: int = 100, offset: int = 0
    ) -> List[DataCollectionError]:
        return self.db.query(DataCollectionError).filter(
            DataCollectionError.batch_id == batch_id
        ).order_by(DataCollectionError.created_at.desc()).offset(offset).limit(limit).all()

    def list(
        self,
        batch_id: Optional[str] = None,
        data_type: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DataCollectionError]:
        query = self.db.query(DataCollectionError)
        if batch_id:
            query = query.filter(DataCollectionError.batch_id == batch_id)
        if data_type:
            query = query.filter(DataCollectionError.data_type == data_type)
        if symbol:
            query = query.filter(DataCollectionError.symbol == symbol)
        return query.order_by(
            DataCollectionError.created_at.desc()
        ).offset(offset).limit(limit).all()

    def count_by_batch(self, batch_id: str) -> int:
        return self.db.query(func.count(DataCollectionError.error_id)).filter(
            DataCollectionError.batch_id == batch_id
        ).scalar()
