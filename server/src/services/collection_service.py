import datetime
import json
import logging
import uuid
from typing import Optional, List

from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.models.data_collection_job import DataCollectionJob
from src.models.data_collection_error import DataCollectionError
from src.models.raw_market_data import RawMarketData
from src.repositories.data_collection_job_repo import DataCollectionJobRepo
from src.repositories.data_collection_error_repo import DataCollectionErrorRepo
from src.repositories.raw_market_data_repo import RawMarketDataRepo
from src.collectors.registry import CollectorRegistry

logger = logging.getLogger(__name__)


class CollectionService:
    MAX_RETRIES_DEFAULT = 3

    def __init__(self, db: Optional[Session] = None):
        self._db = db

    def _get_db(self) -> Session:
        if self._db is not None:
            return self._db
        return SessionLocal()

    @staticmethod
    def _generate_batch_id() -> str:
        today = datetime.datetime.now().strftime("%Y%m%d")
        return f"batch_{today}_{uuid.uuid4().hex[:6]}"

    @staticmethod
    def _generate_task_id() -> str:
        return f"job_{uuid.uuid4().hex[:12]}"

    def create_and_run(
        self,
        data_type: str,
        symbols: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        trigger_type: str = "SCHEDULED",
        max_retries: int = MAX_RETRIES_DEFAULT,
    ) -> DataCollectionJob:
        own_session = self._db is None
        db = self._get_db()
        try:
            job_repo = DataCollectionJobRepo(db)
            task_id = self._generate_task_id()
            params = {}
            if symbols:
                params["symbols"] = symbols
            if date_from:
                params["dateFrom"] = date_from
            if date_to:
                params["dateTo"] = date_to
            job = DataCollectionJob(
                task_id=task_id,
                batch_id=self._generate_batch_id(),
                data_type=data_type,
                source_code="",
                status="PENDING",
                trigger_type=trigger_type,
                max_retries=max_retries,
                params=json.dumps(params, ensure_ascii=False) if params else None,
            )
            job_repo.create(job)
            return self._execute_job(task_id, db)
        finally:
            if own_session:
                db.close()

    def _execute_job(self, task_id: str, db: Optional[Session] = None) -> Optional[DataCollectionJob]:
        own_session = db is None and self._db is None
        if db is None:
            db = self._get_db()
        try:
            job_repo = DataCollectionJobRepo(db)
            job = job_repo.get(task_id)
            if not job:
                logger.error("任务 %s 不存在", task_id)
                return None

            job.status = "RUNNING"
            job.start_time = datetime.datetime.now()
            job_repo.update(job)

            collector_cls = CollectorRegistry.new_instance(job.data_type)
            if not collector_cls:
                job.status = "FAILED"
                job.error_code = "ERR_NO_COLLECTOR"
                job.error_message = f"未注册数据类型 {job.data_type} 的采集器"
                job.end_time = datetime.datetime.now()
                job_repo.update(job)
                return job

            symbols = None
            date_from = None
            date_to = None
            if job.params:
                try:
                    params = json.loads(job.params)
                    symbols = params.get("symbols")
                    date_from = params.get("dateFrom")
                    date_to = params.get("dateTo")
                except (json.JSONDecodeError, TypeError):
                    pass

            result = collector_cls.collect(
                symbols=symbols,
                date_from=date_from,
                date_to=date_to,
            )

            error_repo = DataCollectionErrorRepo(db)
            raw_repo = RawMarketDataRepo(db)

            raw_records = []
            for item in result.success_items:
                raw_records.append(RawMarketData(
                    batch_id=job.batch_id,
                    source_code=result.source_code,
                    data_type=result.data_type,
                    symbol=item.symbol,
                    payload=json.dumps(item.data, ensure_ascii=False, default=str),
                    collected_at=item.collected_at or datetime.datetime.now(),
                ))

            if raw_records:
                raw_repo.batch_create(raw_records)

            error_records = []
            for item in result.failed_items:
                error_records.append(DataCollectionError(
                    batch_id=job.batch_id,
                    symbol=item.symbol,
                    data_type=result.data_type,
                    error_code=item.error_code,
                    error_message=item.error_message,
                ))

            if error_records:
                error_repo.batch_create(error_records)

            job.source_code = result.source_code
            job.success_count = len(raw_records)
            job.fail_count = len(error_records)
            job.total_count = len(raw_records) + len(error_records)

            if not result.failed_items:
                job.status = "SUCCESS"
            elif not result.success_items:
                job.status = "FAILED"
                job.error_code = error_records[0].error_code if error_records else "ERR_UNKNOWN"
                job.error_message = error_records[0].error_message if error_records else "全部采集失败"
            else:
                job.status = "PARTIAL_SUCCESS"

            job.end_time = datetime.datetime.now()
            job_repo.update(job)

            if job.status == "FAILED" and job.retry_count < job.max_retries:
                logger.info("任务 %s 失败，当前重试次数 %d/%d",
                            task_id, job.retry_count, job.max_retries)
                self._retry_job(job_repo, job, db)

            return job

        except Exception as e:
            logger.exception("执行任务 %s 异常", task_id)
            try:
                job = job_repo.get(task_id)
                if job:
                    job.status = "FAILED"
                    job.error_code = "ERR_EXCEPTION"
                    job.error_message = str(e)
                    job.end_time = datetime.datetime.now()
                    job_repo.update(job)
                return job
            except Exception:
                logger.exception("更新任务 %s 异常状态失败", task_id)
                return None
        finally:
            if own_session:
                db.close()

    def _retry_job(self, job_repo: DataCollectionJobRepo, job: DataCollectionJob, db: Session):
        if job.retry_count >= job.max_retries:
            return

        job.retry_count += 1
        job.status = "PENDING"
        job_repo.update(job)

        self._execute_job(job.task_id, db)

    def retry_failed_jobs(self, max_retries: int = 3):
        db = self._get_db()
        try:
            job_repo = DataCollectionJobRepo(db)
            failed_jobs = job_repo.find_retryable_failed(max_retries)
            for job in failed_jobs:
                logger.info("自动重试失败任务 %s (data_type=%s, retry=%d/%d)",
                            job.task_id, job.data_type, job.retry_count, job.max_retries)
                self._execute_job(job.task_id, db)
        finally:
            if self._db is None:
                db.close()
