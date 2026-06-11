import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from src.db.database import Base


class StockQuoteSnapshot(Base):
    __tablename__ = "stock_quote_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True, comment="股票代码")
    latest_price = Column(Float, nullable=True, comment="最新价")
    change_percent = Column(Float, nullable=True, comment="涨跌幅 %")
    volume = Column(Float, nullable=True, comment="成交量（股）")
    amount = Column(Float, nullable=True, comment="成交额（元）")
    turnover_rate = Column(Float, nullable=True, comment="换手率 %")
    volume_ratio = Column(Float, nullable=True, comment="量比")
    high = Column(Float, nullable=True, comment="当日最高")
    low = Column(Float, nullable=True, comment="当日最低")
    open_price = Column(Float, nullable=True, comment="开盘价")
    pre_close = Column(Float, nullable=True, comment="昨收")
    amplitude = Column(Float, nullable=True, comment="振幅 %")
    data_time = Column(DateTime, nullable=False, comment="数据时间")
    delay_minutes = Column(Integer, default=0, comment="延迟分钟数")
    source = Column(String(64), nullable=True, comment="数据来源")
    batch_id = Column(String(64), nullable=True, comment="采集批号")
    quote_type = Column(String(20), default="REALTIME", comment="快照类型 REALTIME/DELAYED/CLOSE")

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "latestPrice": self.latest_price,
            "changePercent": self.change_percent,
            "volume": self.volume,
            "amount": self.amount,
            "turnoverRate": self.turnover_rate,
            "volumeRatio": self.volume_ratio,
            "high": self.high,
            "low": self.low,
            "openPrice": self.open_price,
            "preClose": self.pre_close,
            "amplitude": self.amplitude,
            "dataTime": self.data_time.isoformat() if self.data_time else None,
            "delayMinutes": self.delay_minutes or 0,
        }
