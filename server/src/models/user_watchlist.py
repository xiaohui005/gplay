import datetime

from sqlalchemy import Column, DateTime, Integer, String

from src.db.database import Base


class UserWatchlist(Base):
    __tablename__ = "user_watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True, unique=True, comment="股票代码")
    added_at = Column(DateTime, default=datetime.datetime.utcnow, comment="添加时间")
