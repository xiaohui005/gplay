import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from src.db.database import Base

DEFAULT_STRATEGY_VERSION = "v1.0.0"


class StrategyConfig(Base):
    __tablename__ = "strategy_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(32), nullable=False, unique=True, index=True)
    config_json = Column(Text, nullable=False)
    description = Column(String(256), nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def get_weights(self) -> dict:
        try:
            cfg = json.loads(self.config_json)
            return cfg.get("weights", {})
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_thresholds(self) -> dict:
        try:
            cfg = json.loads(self.config_json)
            return cfg.get("thresholds", {})
        except (json.JSONDecodeError, TypeError):
            return {}


class AnalysisResult(Base):
    __tablename__ = "stock_analysis_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True)
    strategy_version = Column(String(32), nullable=False)
    total_score = Column(Integer, nullable=True)
    suggestion = Column(String(20), nullable=True)
    risk_level = Column(String(10), nullable=True)
    result_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


DEFAULT_CONFIG_JSON = json.dumps(
    {
        "version": DEFAULT_STRATEGY_VERSION,
        "weights": {
            "trend": 25,
            "volumePrice": 20,
            "capital": 20,
            "sector": 15,
            "fundamental": 10,
            "event": 10,
        },
        "thresholds": {
            "buyLightMinScore": 65,
            "buyWatchMinScore": 55,
            "holdMinScore": 45,
            "avoidMaxScore": 44,
            "buyLightStrongThreshold": 60,
            "strongSignalThreshold": 70,
            "riskDelayMinutes": 120,
            "maxRiskPenalty": 100,
        },
    },
    ensure_ascii=False,
)


def create_default_strategy(db_session) -> StrategyConfig:
    existing = (
        db_session.query(StrategyConfig)
        .filter(StrategyConfig.version == DEFAULT_STRATEGY_VERSION)
        .first()
    )
    if existing:
        return existing
    cfg = StrategyConfig(
        version=DEFAULT_STRATEGY_VERSION,
        config_json=DEFAULT_CONFIG_JSON,
        description="默认策略 v1.0.0",
        enabled=True,
    )
    db_session.add(cfg)
    db_session.flush()
    return cfg


def get_active_strategy(db_session) -> StrategyConfig:
    cfg = (
        db_session.query(StrategyConfig)
        .filter(StrategyConfig.enabled == True)
        .order_by(StrategyConfig.created_at.desc())
        .first()
    )
    if cfg is None:
        cfg = create_default_strategy(db_session)
    return cfg
