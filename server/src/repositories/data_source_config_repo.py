from typing import Optional, List
from sqlalchemy.orm import Session
from src.models.data_source_config import DataSourceConfig


class DataSourceConfigRepo:
    def __init__(self, db: Session):
        self.db = db

    def get_by_code(self, code: str) -> Optional[DataSourceConfig]:
        return self.db.query(DataSourceConfig).filter(
            DataSourceConfig.source_code == code,
            DataSourceConfig.enabled == True,
        ).first()

    def get_active_sources(self) -> List[DataSourceConfig]:
        return self.db.query(DataSourceConfig).filter(
            DataSourceConfig.enabled == True,
        ).all()

    def list_all(self) -> List[DataSourceConfig]:
        return self.db.query(DataSourceConfig).order_by(
            DataSourceConfig.source_code
        ).all()

    def create(self, config: DataSourceConfig) -> DataSourceConfig:
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def update(self, config: DataSourceConfig) -> DataSourceConfig:
        self.db.commit()
        self.db.refresh(config)
        return config
