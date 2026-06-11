import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.repositories.data_collection_job_repo import DataCollectionJobRepo
from src.repositories.data_collection_error_repo import DataCollectionErrorRepo
from src.services.collection_service import CollectionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/data-collection", tags=["数据采集管理"])


class ManualTriggerRequest(BaseModel):
    dataType: str = Field(..., description="数据类型: QUOTE/KLINE/FINANCIAL/ANNOUNCEMENT/RISK/SECTOR/STOCK_BASIC/TRADE_STATUS")
    symbols: Optional[List[str]] = Field(default=None, description="股票代码列表，为空表示全量")
    dateFrom: Optional[str] = Field(default=None, description="开始日期 yyyy-MM-dd")
    dateTo: Optional[str] = Field(default=None, description="结束日期 yyyy-MM-dd")
    reason: str = Field(default="manual_recollect", description="补采原因")


class JobResponse(BaseModel):
    taskId: str
    batchId: str
    dataType: str
    source: str
    status: str
    triggerType: str
    successCount: int
    failCount: int
    totalCount: int
    errorCode: Optional[str] = None
    errorMessage: Optional[str] = None
    retryCount: int
    maxRetries: int
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    createdAt: str


class JobListResponse(BaseModel):
    items: List[JobResponse]
    total: int


class ErrorResponse(BaseModel):
    errorId: int
    batchId: str
    symbol: str
    dataType: str
    errorCode: Optional[str] = None
    errorMessage: Optional[str] = None
    retryCount: int
    createdAt: str


class ErrorListResponse(BaseModel):
    items: List[ErrorResponse]
    total: int


@router.post("/jobs", response_model=JobResponse, status_code=201)
def manual_trigger_job(
    req: ManualTriggerRequest,
    db: Session = Depends(get_db),
):
    from src.collectors.registry import CollectorRegistry
    data_type = req.dataType.upper()
    if data_type not in CollectorRegistry.list_types():
        raise HTTPException(
            status_code=400,
            detail=f"无效数据类型: {req.dataType}，已注册类型: {CollectorRegistry.list_types()}",
        )

    service = CollectionService(db=db)
    job = service.create_and_run(
        data_type=req.dataType.upper(),
        symbols=req.symbols,
        date_from=req.dateFrom,
        date_to=req.dateTo,
        trigger_type="MANUAL",
    )
    return _job_to_response(job)


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    dataType: Optional[str] = Query(None, alias="dataType"),
    status: Optional[str] = Query(None),
    sourceCode: Optional[str] = Query(None, alias="sourceCode"),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200, alias="pageSize"),
    db: Session = Depends(get_db),
):
    repo = DataCollectionJobRepo(db)
    offset = (page - 1) * pageSize

    filters = {}
    if dataType:
        filters["data_type"] = dataType.upper()
    if status:
        filters["status"] = status.upper()
    if sourceCode:
        filters["source_code"] = sourceCode

    items = repo.list(
        data_type=filters.get("data_type"),
        status=filters.get("status"),
        source_code=filters.get("source_code"),
        limit=pageSize,
        offset=offset,
    )
    total = repo.count(
        data_type=filters.get("data_type"),
        status=filters.get("status"),
        source_code=filters.get("source_code"),
    )
    return JobListResponse(
        items=[_job_to_response(j) for j in items],
        total=total,
    )


@router.get("/jobs/{task_id}", response_model=JobResponse)
def get_job(task_id: str, db: Session = Depends(get_db)):
    repo = DataCollectionJobRepo(db)
    job = repo.get(task_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return _job_to_response(job)


@router.post("/jobs/{task_id}/retry", response_model=JobResponse)
def retry_job(task_id: str, db: Session = Depends(get_db)):
    repo = DataCollectionJobRepo(db)
    job = repo.get(task_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    if job.status not in ("FAILED", "PARTIAL_SUCCESS"):
        raise HTTPException(status_code=400, detail=f"任务 {task_id} 状态为 {job.status}，不可重试")

    service = CollectionService()
    service._execute_job(task_id, db)
    db.refresh(job)
    return _job_to_response(job)


@router.get("/errors", response_model=ErrorListResponse)
def list_errors(
    batchId: Optional[str] = Query(None, alias="batchId"),
    dataType: Optional[str] = Query(None, alias="dataType"),
    symbol: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=200, alias="pageSize"),
    db: Session = Depends(get_db),
):
    repo = DataCollectionErrorRepo(db)
    offset = (page - 1) * pageSize
    items = repo.list(
        batch_id=batchId,
        data_type=dataType.upper() if dataType else None,
        symbol=symbol,
        limit=pageSize,
        offset=offset,
    )
    total = len(items)
    return ErrorListResponse(
        items=[_error_to_response(e) for e in items],
        total=total,
    )


def _job_to_response(job) -> JobResponse:
    return JobResponse(
        taskId=job.task_id,
        batchId=job.batch_id,
        dataType=job.data_type,
        source=job.source_code or "",
        status=job.status,
        triggerType=job.trigger_type,
        successCount=job.success_count or 0,
        failCount=job.fail_count or 0,
        totalCount=job.total_count or 0,
        errorCode=job.error_code,
        errorMessage=job.error_message,
        retryCount=job.retry_count or 0,
        maxRetries=job.max_retries or 3,
        startTime=job.start_time.isoformat() if job.start_time else None,
        endTime=job.end_time.isoformat() if job.end_time else None,
        createdAt=job.created_at.isoformat() if job.created_at else "",
    )


def _error_to_response(err) -> ErrorResponse:
    return ErrorResponse(
        errorId=err.error_id,
        batchId=err.batch_id,
        symbol=err.symbol,
        dataType=err.data_type,
        errorCode=err.error_code,
        errorMessage=err.error_message,
        retryCount=err.retry_count or 0,
        createdAt=err.created_at.isoformat() if err.created_at else "",
    )
