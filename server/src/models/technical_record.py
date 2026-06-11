import datetime
import json

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean

from src.db.database import Base


class TechnicalRecord(Base):
    __tablename__ = "technical_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True, comment="股票代码")
    name = Column(String(64), nullable=False, comment="股票名称")
    created_at = Column(DateTime, default=datetime.datetime.now, index=True, comment="保存时间")

    price_at_analysis = Column(Float, nullable=False, comment="分析时的最新收盘价")
    predicted_direction = Column(String(16), nullable=False, comment="预测方向: UP/DOWN/SIDEWAYS")
    confidence_score = Column(Float, nullable=False, comment="信心度 0-100")
    indicators_json = Column(Text, nullable=False, comment="所有指标快照(JSON)")
    summary = Column(Text, nullable=False, comment="分析师风格总评")

    actual_direction = Column(String(16), nullable=True, comment="实际方向: UP/DOWN/SIDEWAYS")
    is_correct = Column(Boolean, nullable=True, comment="判断是否正确")
    verified_at = Column(DateTime, nullable=True, comment="验证时间")

    def to_dict(self):
        indicators = json.loads(self.indicators_json) if self.indicators_json else {}
        key_evidence = indicators.pop("_keyEvidence", [])
        risk_warning = indicators.pop("_riskWarning", [])
        recommendation = indicators.pop("_recommendation", "建议观望")
        signals = indicators.pop("_signals", {"buyPrice": 0, "sellPrice": 0, "stopLoss": 0})
        analysis_session = indicators.pop("_analysisSession", None)
        analysis_time_label = indicators.pop("_analysisTimeLabel", None)
        direction = self.predicted_direction
        recommendation = recommendation
        summary = self.summary
        if direction in ("UP", "DOWN") and self.confidence_score < 55:
            direction = "SIDEWAYS"
            recommendation = "建议观望"
            if not summary.startswith("信号强度不足"):
                summary = f"信号强度不足，暂不做方向判断；{summary}"

        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "priceAtAnalysis": self.price_at_analysis,
            "direction": direction,
            "confidence": self.confidence_score,
            "recommendation": recommendation,
            "signals": signals,
            "indicators": indicators,
            "keyEvidence": key_evidence,
            "riskWarning": risk_warning,
            "summary": summary,
            "isCorrect": self.is_correct,
            "actualDirection": self.actual_direction,
            "verifiedAt": self.verified_at.isoformat() if self.verified_at else None,
            "analysisSession": analysis_session,
            "analysisTimeLabel": analysis_time_label,
        }
