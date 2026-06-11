import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models.data_collection_job import DataCollectionJob


class DataCollectionJobRepo:
    def __init__(self, db: Session):
        self.db = db

    def get(self, task_id: str) -> Optional[DataCollectionJob]:
        return self.db.query(DataCollectionJob).filter(
            DataCollectionJob.task_id == task_id
        ).first()

    def list(
        self,
        data_type: Optional[str] = None,
        status: Optional[str] = None,
        source_code: Optional[str] = None,
        trigger_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DataCollectionJob]:
        query = self.db.query(DataCollectionJob)
        if data_type:
            query = query.filter(DataCollectionJob.data_type == data_type)
        if status:
            query = query.filter(DataCollectionJob.status == status)
        if source_code:
            query = query.filter(DataCollectionJob.source_code == source_code)
        if trigger_type:
            query = query.filter(DataCollectionJob.trigger_type == trigger_type)
        return query.order_by(
            DataCollectionJob.created_at.desc()
        ).offset(offset).limit(limit).all()

    def count(
        self,
        data_type: Optional[str] = None,
        status: Optional[str] = None,
        source_code: Optional[str] = None,
    ) -> int:
        query = self.db.query(func.count(DataCollectionJob.task_id))
        if data_type:
            query = query.filter(DataCollectionJob.data_type == data_type)
        if status:
            query = query.filter(DataCollectionJob.status == status)
        if source_code:
            query = query.filter(DataCollectionJob.source_code == source_code)
        return query.scalar()

    def create(self, job: DataCollectionJob) -> DataCollectionJob:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def update(self, job: DataCollectionJob) -> DataCollectionJob:
        job.updated_at = datetime.datetime.utcnow()
        self.db.commit()
        self.db.refresh(job)
        return job

    def find_retryable_failed(self, max_retries: int = 3) -> List[DataCollectionJob]:
        return self.db.query(DataCollectionJob).filter(
            DataCollectionJob.status == "FAILED",
            DataCollectionJob.retry_count < max_retries,
        ).order_by(DataCollectionJob.updated_at.asc()).limit(20).all()
