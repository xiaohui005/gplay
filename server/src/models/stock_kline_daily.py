from sqlalchemy import Column, Float, Integer, String, UniqueConstraint
from src.db.database import Base


class StockKlineDaily(Base):
    __tablename__ = "stock_kline_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True)
    trade_date = Column(String(10), nullable=False)
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    amount = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_symbol_trade_date"),
    )

    def to_dict(self):
        return {
            "tradeDate": self.trade_date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "amount": self.amount,
        }
