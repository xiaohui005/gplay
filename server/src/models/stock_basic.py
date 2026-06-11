import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from src.db.database import Base


class StockBasic(Base):
    __tablename__ = "stock_basic"

    symbol = Column(String(16), primary_key=True, comment="股票代码")
    name = Column(String(64), nullable=False, index=True, comment="股票名称")
    market = Column(String(10), nullable=False, comment="市场 SSE/SZSE/BSE")
    trade_status = Column(String(20), default="TRADING", comment="交易状态 TRADING/SUSPENDED/DELISTED")
    pinyin = Column(String(64), nullable=True, comment="拼音简写")
    list_date = Column(String(10), nullable=True, comment="上市日期")
    total_shares = Column(Float, nullable=True, comment="总股本")
    update_time = Column(DateTime, default=datetime.datetime.utcnow, comment="更新时间")

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market,
            "tradeStatus": self.trade_status,
            "pinyin": self.pinyin or "",
        }
