import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from src.db.database import Base


class DataCollectionError(Base):
    __tablename__ = "data_collection_error"

    error_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), nullable=False, index=True, comment="关联采集批次")
    symbol = Column(String(16), nullable=False, comment="股票代码")
    data_type = Column(String(32), nullable=False)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
