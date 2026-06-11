import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SAEnum
from src.db.database import Base


class DataCollectionJob(Base):
    __tablename__ = "data_collection_job"

    task_id = Column(String(64), primary_key=True, comment="采集任务 ID")
    batch_id = Column(String(64), nullable=False, comment="批次号 batch_yyyyMMdd_nnn")
    data_type = Column(String(32), nullable=False, comment="QUOTE / KLINE / FINANCIAL / ANNOUNCEMENT / RISK / SECTOR / STOCK_BASIC / TRADE_STATUS")
    source_code = Column(String(64), nullable=False, comment="数据源标识")
    status = Column(String(20), nullable=False, default="PENDING", comment="PENDING / RUNNING / SUCCESS / PARTIAL_SUCCESS / FAILED / SKIPPED")
    trigger_type = Column(String(10), nullable=False, default="SCHEDULED", comment="SCHEDULED / MANUAL")
    params = Column(Text, nullable=True, comment="采集参数 JSON: symbols, dateFrom, dateTo")
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
