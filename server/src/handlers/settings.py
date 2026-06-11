from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.models.notification_config import NotificationConfig
from src.services.bark_service import BarkService


router = APIRouter(prefix="/api/settings", tags=["settings"])


class NotificationSettingsPayload(BaseModel):
    barkEnabled: bool = False
    barkServerUrl: str = ""
    barkDeviceKey: str = ""


@router.get("/notification")
def get_notification_settings(db: Session = Depends(get_db)):
    config = _get_or_create_config(db)
    return config.to_dict()


@router.put("/notification")
def save_notification_settings(payload: NotificationSettingsPayload, db: Session = Depends(get_db)):
    config = _get_or_create_config(db)
    config.bark_enabled = payload.barkEnabled
    config.bark_server_url = payload.barkServerUrl.strip()
    config.bark_device_key = payload.barkDeviceKey.strip()
    db.commit()
    db.refresh(config)
    return config.to_dict()


@router.post("/notification/test")
def test_notification_settings(db: Session = Depends(get_db)):
    config = _get_or_create_config(db)
    return BarkService(config).send_test()


def _get_or_create_config(db: Session) -> NotificationConfig:
    config = db.query(NotificationConfig).order_by(NotificationConfig.id.asc()).first()
    if config:
        return config
    config = NotificationConfig()
    db.add(config)
    db.commit()
    db.refresh(config)
    return config
