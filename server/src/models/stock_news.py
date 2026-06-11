import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from src.db.database import Base


class StockNews(Base):
    __tablename__ = "stock_news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    source = Column(String(64), nullable=True)
    publish_time = Column(DateTime, nullable=True)
    url = Column(String(1024), nullable=True)
    content_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "title", "publish_time", name="uq_news_dedup"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source or "",
            "publishTime": self.publish_time.isoformat() if self.publish_time else None,
            "url": self.url or "",
            "contentSummary": self.content_summary or "",
        }
