import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from src.db.database import Base


class NotificationConfig(Base):
    __tablename__ = "notification_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bark_enabled = Column(Boolean, default=False, nullable=False)
    bark_server_url = Column(String(512), nullable=True)
    bark_device_key = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "barkEnabled": bool(self.bark_enabled),
            "barkServerUrl": self.bark_server_url or "",
            "barkDeviceKey": self.bark_device_key or "",
        }
