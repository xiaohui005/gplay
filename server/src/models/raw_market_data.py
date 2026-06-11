import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from src.db.database import Base


class RawMarketData(Base):
    __tablename__ = "raw_market_data"

    raw_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), nullable=False, index=True, comment="关联采集批次")
    source_code = Column(String(64), nullable=False)
    data_type = Column(String(32), nullable=False)
    symbol = Column(String(16), nullable=False, comment="股票代码")
    payload = Column(Text, nullable=False, comment="原始响应 JSON")
    collected_at = Column(DateTime, nullable=False, comment="数据时间（数据源的 dataTime）")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
