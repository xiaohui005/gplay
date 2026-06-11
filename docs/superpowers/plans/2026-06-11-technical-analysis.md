# 技术研判（Technical Analysis）实施计划

> **对于代理工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 来逐任务实施此计划。步骤使用复选框（`- [ ]`）语法进行跟踪。

**目标：** 新增独立的技术研判页面，从专业分析师角度综合多指标判断股票短期方向，并记录每次分析以便验证准确率。

**架构：** 后端新增 TechnicalRecord 模型 + technical_engine 指标计算 + technical_analysis handler → 前端新增 TechnicalAnalysisPage + AnalysisHistoryPage + 详情页入口按钮

**技术栈：** Python 3.13 + FastAPI + SQLAlchemy + SQLite, Vite + React 19 + TypeScript

---

### 任务 1：后端模型 — TechnicalRecord

**文件：**
- 创建：`server/src/models/technical_record.py`
- 修改：`server/src/models/__init__.py`

- [ ] **步骤 1：创建模型文件**

```python
# server/src/models/technical_record.py
import datetime
import json

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean

from src.db.database import Base


class TechnicalRecord(Base):
    __tablename__ = "technical_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True, comment="股票代码")
    name = Column(String(64), nullable=False, comment="股票名称")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True, comment="分析时间")

    price_at_analysis = Column(Float, nullable=False, comment="分析时的最新收盘价")
    predicted_direction = Column(String(16), nullable=False, comment="预测方向: UP/DOWN/SIDEWAYS")
    confidence_score = Column(Float, nullable=False, comment="信心度 0-100")
    indicators_json = Column(Text, nullable=False, comment="所有指标快照(JSON)")
    summary = Column(Text, nullable=False, comment="分析师风格总评")

    actual_direction = Column(String(16), nullable=True, comment="实际方向: UP/DOWN/SIDEWAYS")
    is_correct = Column(Boolean, nullable=True, comment="判断是否正确")
    verified_at = Column(DateTime, nullable=True, comment="验证时间")

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "priceAtAnalysis": self.price_at_analysis,
            "direction": self.predicted_direction,
            "confidence": self.confidence_score,
            "indicators": json.loads(self.indicators_json) if self.indicators_json else {},
            "summary": self.summary,
            "isCorrect": self.is_correct,
            "actualDirection": self.actual_direction,
            "verifiedAt": self.verified_at.isoformat() if self.verified_at else None,
        }
```

- [ ] **步骤 2：注册模型**

修改 `server/src/models/__init__.py`，添加：

```python
from src.models.technical_record import TechnicalRecord
```

并在 `__all__` 列表尾部追加 `"TechnicalRecord"`。

- [ ] **步骤 3：验证导入**

运行：`python -c "from src.models import TechnicalRecord; print('OK')"`
预期输出：`OK`

---

### 任务 2：后端引擎 — 技术指标计算

**文件：**
- 创建：`server/src/analysis/technical_engine.py`

- [ ] **步骤 1：创建引擎文件**

```python
# server/src/analysis/technical_engine.py
import logging
import math

logger = logging.getLogger(__name__)


def _ma(data: list[float], n: int) -> float | None:
    if len(data) < n:
        return None
    return sum(data[-n:]) / n


def _calc_macd(closes: list[float]) -> dict:
    """计算 MACD（简化版：12日EMA - 26日EMA）"""
    if len(closes) < 26:
        return {"histogram": 0, "direction": "neutral", "detail": "K线数据不足26根，无法计算MACD"}
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    dif = ema12[-1] - ema26[-1]
    dea = _ma([ema12[i] - ema26[i] for i in range(len(ema12))], 9)
    if dea is None:
        dea = 0
    histogram = dif - dea
    prev_hist = (ema12[-2] - ema26[-2]) - dea if len(closes) > 1 else histogram
    direction = "rising" if histogram > prev_hist else "falling"
    status = "bullish" if dif > dea and histogram > 0 else "bearish" if dif < dea and histogram < 0 else "neutral"
    return {
        "dif": round(dif, 4),
        "dea": round(dea, 4),
        "histogram": round(histogram, 4),
        "direction": direction,
        "status": status,
        "detail": f"MACD {'金叉多头' if status == 'bullish' else '死叉空头' if status == 'bearish' else '粘合'}"
    }


def _ema(data: list[float], n: int) -> list[float]:
    result = []
    multiplier = 2 / (n + 1)
    ema = sum(data[:n]) / n
    result.append(ema)
    for price in data[n:]:
        ema = (price - ema) * multiplier + ema
        result.append(ema)
    return result


def _calc_rsi(closes: list[float], n: int = 14) -> dict:
    if len(closes) < n + 1:
        return {"value": 50, "status": "neutral", "detail": "K线数据不足，RSI默认中性"}
    gains, losses = 0, 0
    for i in range(-n, 0):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / n
    avg_loss = losses / n
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    if rsi > 70:
        status = "overbought"
        detail = f"RSI {rsi:.1f}，超买区，注意回调风险"
    elif rsi < 30:
        status = "oversold"
        detail = f"RSI {rsi:.1f}，超卖区，关注反弹机会"
    else:
        status = "neutral"
        detail = f"RSI {rsi:.1f}，中性区间"
    return {"value": round(rsi, 1), "status": status, "detail": detail}


def _calc_bollinger(closes: list[float], n: int = 20) -> dict:
    if len(closes) < n:
        return {"position": "middle", "width": 0, "detail": "K线数据不足，无法计算布林带"}
    recent = closes[-n:]
    ma = sum(recent) / n
    variance = sum((x - ma) ** 2 for x in recent) / n
    std = math.sqrt(variance)
    upper = ma + 2 * std
    lower = ma - 2 * std
    latest = closes[-1]
    if latest >= upper:
        position = "upper"
        detail = "价格触及布林带上轨，偏强"
    elif latest <= lower:
        position = "lower"
        detail = "价格触及布林带下轨，偏弱"
    else:
        position = "middle"
        detail = "价格运行在布林带中轨附近"
    width = round((upper - lower) / ma * 100, 2) if ma else 0
    return {"position": position, "upper": round(upper, 2), "middle": round(ma, 2), "lower": round(lower, 2), "width": width, "detail": detail}


def _calc_volume_analysis(volumes: list[float], closes: list[float]) -> dict:
    if len(volumes) < 20:
        return {"volumeRatio": 1.0, "volumeTrend": "unknown", "priceVolumeConfirm": True, "detail": "量能数据不足"}
    vol_5 = sum(volumes[-5:]) / 5
    vol_20 = sum(volumes[-20:]) / 20
    vol_ratio = round(vol_5 / vol_20, 2) if vol_20 else 1.0
    vol_trend = "increasing" if vol_ratio > 1.3 else "decreasing" if vol_ratio < 0.7 else "stable"
    price_change = closes[-1] - closes[-5]
    confirm = (price_change > 0 and vol_ratio > 1) or (price_change < 0 and vol_ratio < 1)
    parts = []
    parts.append(f"量比 {vol_ratio}")
    parts.append("放量" if vol_ratio > 1.3 else "缩量" if vol_ratio < 0.7 else "量能平稳")
    parts.append("价量配合" if confirm else "价量背离")
    return {
        "volumeRatio": vol_ratio,
        "volumeTrend": vol_trend,
        "priceVolumeConfirm": confirm,
        "detail": "，".join(parts)
    }


def _calc_support_resistance(closes: list[float], highs: list[float], lows: list[float]) -> dict:
    if len(closes) < 10:
        return {"nearestSupport": 0, "nearestResistance": 0, "distanceToSupport": 0, "distanceToResistance": 0, "detail": "数据不足"}
    recent_high = max(highs[-10:])
    recent_low = min(lows[-10:])
    latest = closes[-1]
    dist_support = round((latest - recent_low) / latest * 100, 2) if latest else 0
    dist_resistance = round((recent_high - latest) / latest * 100, 2) if latest else 0
    return {
        "nearestSupport": round(recent_low, 2),
        "nearestResistance": round(recent_high, 2),
        "distanceToSupport": dist_support,
        "distanceToResistance": dist_resistance,
        "detail": f"近10日支撑 {recent_low}，压力 {recent_high}"
    }


def analyze_technical(klines: list[dict]) -> dict:
    closes = [b["close"] for b in klines if b.get("close") is not None]
    highs = [b["high"] for b in klines if b.get("high") is not None]
    lows = [b["low"] for b in klines if b.get("low") is not None]
    volumes = [b["volume"] for b in klines if b.get("volume") is not None]

    if len(closes) < 10:
        return _empty_result("K线数据不足10根，无法分析")

    latest_close = closes[-1]
    ma5 = _ma(closes, 5)
    ma10 = _ma(closes, 10)
    ma20 = _ma(closes, 20)

    # Trend
    if ma5 and ma10 and ma20:
        if ma5 > ma10 > ma20:
            trend_status = "bullish"
            trend_detail = "MA5 > MA10 > MA20 多头排列"
        elif ma5 < ma10 < ma20:
            trend_status = "bearish"
            trend_detail = "MA5 < MA10 < MA20 空头排列"
        else:
            trend_status = "neutral"
            trend_detail = "均线交叉，方向不明"
        # Golden/death cross
        if len(closes) >= 10:
            prev_ma5 = _ma(closes[:-1], 5) or 0
            prev_ma10 = _ma(closes[:-1], 10) or 0
            cross = "none"
            if prev_ma5 <= prev_ma10 and ma5 > ma10:
                cross = "golden_cross"
            elif prev_ma5 >= prev_ma10 and ma5 < ma10:
                cross = "death_cross"
        else:
            cross = "none"
    else:
        trend_status = "neutral"
        trend_detail = "均线数据不足"
        cross = "none"

    trend_vote = 1 if trend_status == "bullish" else (-1 if trend_status == "bearish" else 0)

    # Momentum
    macd = _calc_macd(closes)
    rsi = _calc_rsi(closes)
    macd_vote = 1 if macd["status"] == "bullish" else (-1 if macd["status"] == "bearish" else 0)
    rsi_vote = 1 if rsi["status"] == "oversold" else (-1 if rsi["status"] == "overbought" else 0)

    # Volatility
    bb = _calc_bollinger(closes)
    bb_vote = 1 if bb["position"] == "lower" else (-1 if bb["position"] == "upper" else 0)

    # Volume
    vol_analysis = _calc_volume_analysis(volumes, closes)
    vol_vote = 1 if (vol_analysis["priceVolumeConfirm"] and vol_analysis["volumeRatio"] > 1) else (-1 if not vol_analysis["priceVolumeConfirm"] else 0)

    # Support/Resistance
    sr = _calc_support_resistance(closes, highs, lows)
    sr_vote = 1 if sr["distanceToSupport"] < sr["distanceToResistance"] else (-1 if sr["distanceToResistance"] < sr["distanceToSupport"] else 0)

    # Composite scoring
    w_trend = trend_vote * 3
    w_macd = macd_vote * 1.5
    w_rsi = rsi_vote * 0.5
    w_bb = bb_vote * 1
    w_vol = vol_vote * 1.5
    w_sr = sr_vote * 1.5

    total_weighted = w_trend + w_macd + w_rsi + w_bb + w_vol + w_sr
    max_possible = 3 + 1.5 + 0.5 + 1 + 1.5 + 1.5  # = 10

    if total_weighted > 1:
        direction = "UP"
        confidence = min(abs(total_weighted) / max_possible * 100, 100)
    elif total_weighted < -1:
        direction = "DOWN"
        confidence = min(abs(total_weighted) / max_possible * 100, 100)
    else:
        direction = "SIDEWAYS"
        confidence = 50

    confidence = round(confidence, 0)

    # Build evidence and risks
    key_evidence = []
    risk_warning = []
    if trend_status == "bullish":
        key_evidence.append(trend_detail)
    elif trend_status == "bearish":
        risk_warning.append(trend_detail)
    if cross == "golden_cross":
        key_evidence.append("MA5上穿MA10金叉")
    elif cross == "death_cross":
        risk_warning.append("MA5下穿MA10死叉")
    if macd["status"] == "bullish":
        key_evidence.append("MACD金叉多头")
    elif macd["status"] == "bearish":
        risk_warning.append("MACD死叉空头")
    if rsi["status"] == "overbought":
        risk_warning.append(rsi["detail"])
    elif rsi["status"] == "oversold":
        key_evidence.append(rsi["detail"])
    if bb["position"] == "upper":
        risk_warning.append("价格触及布林带上轨")
    elif bb["position"] == "lower":
        key_evidence.append("价格触及布林带下轨")
    if vol_analysis["priceVolumeConfirm"] and vol_analysis["volumeRatio"] > 1.3:
        key_evidence.append("价量配合，放量上涨")
    elif not vol_analysis["priceVolumeConfirm"] and vol_analysis["volumeRatio"] < 0.7:
        risk_warning.append("价量背离，缩量下跌")

    if not key_evidence:
        key_evidence.append("各指标信号不明确，市场方向待确认")
    if not risk_warning:
        risk_warning.append("当前无明显风险信号")

    # Summary
    dir_map = {"UP": "看涨↑", "DOWN": "看跌↓", "SIDEWAYS": "盘整→"}
    summary_parts = [f"综合研判：{dir_map.get(direction, '中性')}，信心度{confidence:.0f}%"]
    if direction == "UP":
        summary_parts.append("多项指标共振偏多" if total_weighted > 4 else "部分指标偏多，但信号强度一般")
    elif direction == "DOWN":
        summary_parts.append("多项指标共振偏空" if total_weighted < -4 else "部分指标偏空，但信号强度一般")
    else:
        summary_parts.append("多空力量均衡，建议观望")
    summary_parts.append(f"趋势{trend_detail}，{macd['detail']}，{rsi['detail']}，{bb['detail']}，{vol_analysis['detail']}")

    return {
        "direction": direction,
        "confidence": confidence,
        "summary": "；".join(summary_parts),
        "keyEvidence": key_evidence,
        "riskWarning": risk_warning,
        "indicators": {
            "trend": {
                "maAlignment": trend_status,
                "maCross": cross,
                "ma5": round(ma5, 2) if ma5 else None,
                "ma10": round(ma10, 2) if ma10 else None,
                "ma20": round(ma20, 2) if ma20 else None,
                "detail": trend_detail,
            },
            "momentum": {
                "macd": macd,
                "rsi": rsi,
            },
            "volatility": bb,
            "volume": vol_analysis,
            "supportResistance": sr,
        },
    }


def _empty_result(reason: str) -> dict:
    return {
        "direction": "SIDEWAYS",
        "confidence": 0,
        "summary": reason,
        "keyEvidence": [],
        "riskWarning": [reason],
        "indicators": {
            "trend": {"maAlignment": "neutral", "maCross": "none", "ma5": None, "ma10": None, "ma20": None, "detail": reason},
            "momentum": {"macd": {"histogram": 0, "direction": "neutral", "status": "neutral", "detail": reason}, "rsi": {"value": 50, "status": "neutral", "detail": reason}},
            "volatility": {"position": "middle", "width": 0, "detail": reason},
            "volume": {"volumeRatio": 1.0, "volumeTrend": "unknown", "priceVolumeConfirm": True, "detail": reason},
            "supportResistance": {"nearestSupport": 0, "nearestResistance": 0, "distanceToSupport": 0, "distanceToResistance": 0, "detail": reason},
        },
    }
```

- [ ] **步骤 2：验证导入**

运行：`python -c "from src.analysis.technical_engine import analyze_technical; print('OK')"`
预期输出：`OK`

---

### 任务 3：后端 Handler — API 端点

**文件：**
- 创建：`server/src/handlers/technical_analysis.py`

- [ ] **步骤 1：创建 handler**

```python
# server/src/handlers/technical_analysis.py
import datetime
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.analysis.technical_engine import analyze_technical
from src.data_sources.east_money import fetch_kline
from src.db.database import get_db
from src.models import StockBasic, TechnicalRecord

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stocks", tags=["technical-analysis"])


@router.get("/{symbol}/technical-analysis")
def get_technical_analysis(symbol: str, db: Session = Depends(get_db)):
    basic = db.query(StockBasic).filter(StockBasic.symbol == symbol).first()
    if not basic:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 未找到")

    # Dedup: check last 10 seconds
    recent = db.query(TechnicalRecord).filter(
        TechnicalRecord.symbol == symbol,
        TechnicalRecord.created_at >= datetime.datetime.utcnow() - datetime.timedelta(seconds=10),
    ).order_by(TechnicalRecord.created_at.desc()).first()
    if recent:
        return recent.to_dict()

    klines = fetch_kline(symbol, datalen=120)
    if not klines:
        raise HTTPException(status_code=400, detail=f"股票 {symbol} K线数据获取失败")

    latest_close = None
    for k in klines:
        if k.get("close") is not None:
            latest_close = k["close"]
    if latest_close is None:
        raise HTTPException(status_code=400, detail=f"股票 {symbol} 无有效收盘价")

    result = analyze_technical(klines)

    record = TechnicalRecord(
        symbol=symbol,
        name=basic.name,
        price_at_analysis=latest_close,
        predicted_direction=result["direction"],
        confidence_score=result["confidence"],
        indicators_json=json.dumps(result["indicators"], ensure_ascii=False),
        summary=result["summary"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    resp = record.to_dict()
    resp["keyEvidence"] = result["keyEvidence"]
    resp["riskWarning"] = result["riskWarning"]
    return resp


@router.get("/technical-analysis/history")
def list_history(
    symbol: str = Query(None, description="股票代码"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(TechnicalRecord)
    if symbol:
        query = query.filter(TechnicalRecord.symbol == symbol)
    total = query.count()
    query = query.order_by(TechnicalRecord.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    records = query.all()

    # Auto-verify unverified records older than 1 hour
    now = datetime.datetime.utcnow()
    for rec in records:
        if rec.is_correct is not None:
            continue
        if rec.created_at and (now - rec.created_at).total_seconds() < 3600:
            continue
        klines = fetch_kline(rec.symbol, datalen=5)
        for k in klines:
            if k.get("close") is not None:
                latest = k["close"]
                break
        else:
            continue
        change_pct = (latest - rec.price_at_analysis) / rec.price_at_analysis * 100
        if change_pct > 0.5:
            actual = "UP"
        elif change_pct < -0.5:
            actual = "DOWN"
        else:
            actual = "SIDEWAYS"
        rec.actual_direction = actual
        rec.is_correct = (actual == rec.predicted_direction)
        rec.verified_at = now
        db.commit()

    items = [r.to_dict() for r in records]

    # Stats
    verified = [r for r in records if r.is_correct is not None]
    correct_count = sum(1 for r in verified if r.is_correct)

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "stats": {
            "totalRecords": total,
            "verifiedCount": len(verified),
            "correctCount": correct_count,
            "accuracy": round(correct_count / len(verified) * 100, 1) if verified else None,
        },
    }


@router.get("/technical-analysis/history/{record_id}")
def get_history_detail(record_id: int, db: Session = Depends(get_db)):
    rec = db.query(TechnicalRecord).filter(TechnicalRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="记录未找到")
    return rec.to_dict()
```

- [ ] **步骤 2：验证 handler 导入**

运行：`python -c "from src.handlers.technical_analysis import router; print('OK')"`
预期输出：`OK`

---

### 任务 4：后端 Wiring

**文件：**
- 修改：`server/src/main.py`

- [ ] **步骤 1：在 main.py 中注册路由**

在 `from src.handlers.t_analysis import router as t_analysis_router` 之后插入：

```python
from src.handlers.technical_analysis import router as technical_analysis_router
```

在 `app.include_router(t_analysis_router)` 之后插入：

```python
app.include_router(technical_analysis_router)
```

- [ ] **步骤 2：重启后端并测试**

运行：`netstat -ano | Select-String ":8008"` 确认 PID，重启后端：
```
taskkill /F /PID 1424
```
然后启动：
```
python -m uvicorn src.main:app --port 8008
```

测试端点：
```
curl.exe http://localhost:8008/api/technical-analysis/history
```
预期输出：`{"items":[],"total":0,"page":1,"limit":20,"stats":...}`

---

### 任务 5：前端类型定义

**文件：**
- 修改：`frontend/src/types/api.ts`

- [ ] **步骤 1：新增类型**

在 `TSignals` 接口之后，`KlineBar` 之前插入：

```typescript
export interface TechnicalIndicators {
  trend: {
    maAlignment: string
    maCross: string
    ma5: number | null
    ma10: number | null
    ma20: number | null
    detail: string
  }
  momentum: {
    macd: {
      dif: number
      dea: number
      histogram: number
      direction: string
      status: string
      detail: string
    }
    rsi: {
      value: number
      status: string
      detail: string
    }
  }
  volatility: {
    position: string
    upper: number
    middle: number
    lower: number
    width: number
    detail: string
  }
  volume: {
    volumeRatio: number
    volumeTrend: string
    priceVolumeConfirm: boolean
    detail: string
  }
  supportResistance: {
    nearestSupport: number
    nearestResistance: number
    distanceToSupport: number
    distanceToResistance: number
    detail: string
  }
}

export interface TechnicalAnalysisResult {
  id: number
  symbol: string
  name: string
  createdAt: string
  priceAtAnalysis: number
  direction: string
  confidence: number
  indicators: TechnicalIndicators
  summary: string
  keyEvidence: string[]
  riskWarning: string[]
  isCorrect: boolean | null
  actualDirection: string | null
}

export interface AnalysisHistoryResponse {
  items: TechnicalAnalysisResult[]
  total: number
  page: number
  limit: number
  stats: {
    totalRecords: number
    verifiedCount: number
    correctCount: number
    accuracy: number | null
  }
}
```

---

### 任务 6：前端 API Client

**文件：**
- 修改：`frontend/src/api/client.ts`

- [ ] **步骤 1：新增方法**

在文件末尾，`getNews` 之后添加：

```typescript
import type { TechnicalAnalysisResult, AnalysisHistoryResponse } from '../types/api'

export function getTechnicalAnalysis(symbol: string): Promise<TechnicalAnalysisResult> {
  return get(`/stocks/${symbol}/technical-analysis`)
}

export function getAnalysisHistory(symbol?: string, page = 1, limit = 20): Promise<AnalysisHistoryResponse> {
  const params = new URLSearchParams()
  if (symbol) params.set('symbol', symbol)
  params.set('page', String(page))
  params.set('limit', String(limit))
  return get(`/technical-analysis/history?${params.toString()}`)
}
```

（注意：`import type` 需要添加到文件顶部已有的 import 语句中。）

---

### 任务 7：前端 TechnicalAnalysisPage

**文件：**
- 创建：`frontend/src/pages/TechnicalAnalysisPage.tsx`

- [ ] **步骤 1：创建页面组件**

```typescript
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getTechnicalAnalysis } from '../api/client'
import type { TechnicalAnalysisResult } from '../types/api'

export default function TechnicalAnalysisPage() {
  const { symbol } = useParams<{ symbol: string }>()
  const nav = useNavigate()
  const [result, setResult] = useState<TechnicalAnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!symbol) return
    setLoading(true)
    setError('')
    getTechnicalAnalysis(symbol)
      .then(setResult)
      .catch(e => setError(e instanceof Error ? e.message : '分析失败'))
      .finally(() => setLoading(false))
  }, [symbol])

  if (loading) return <div className="page"><p className="hint">分析中...</p></div>
  if (error) return (
    <div className="page ta-page">
      <button className="back-btn" onClick={() => nav(-1)}>← 返回</button>
      <p className="hint error">{error}</p>
    </div>
  )
  if (!result) return null

  const dirMap: Record<string, { label: string; cls: string }> = {
    UP: { label: '看涨 ↑', cls: 'ta-up' },
    DOWN: { label: '看跌 ↓', cls: 'ta-down' },
    SIDEWAYS: { label: '盘整 →', cls: 'ta-sideways' },
  }
  const dir = dirMap[result.direction] || { label: '未知', cls: '' }

  return (
    <div className="page ta-page">
      <div className="toolbar">
        <button className="back-btn" onClick={() => nav(-1)}>← 返回</button>
        <button className="collect-btn" onClick={() => { setLoading(true); setError(''); getTechnicalAnalysis(symbol!).then(setResult).catch(e => setError(e.message)).finally(() => setLoading(false)) }}>
          重新分析
        </button>
      </div>

      {/* Header */}
      <div className="ta-header">
        <h2>{result.symbol} <span className="dim">{result.name}</span></h2>
        <span className="dim">分析时间: {result.createdAt ? new Date(result.createdAt).toLocaleString('zh-CN') : ''}</span>
      </div>

      {/* Direction call */}
      <div className={`ta-direction-card ${dir.cls}`}>
        <div className="ta-direction-badge">{dir.label}</div>
        <div className="ta-confidence-section">
          <span className="ta-confidence-label">信心度</span>
          <div className="ta-confidence-bar-wrap">
            <div className="ta-confidence-bar" style={{ width: `${result.confidence}%` }} />
          </div>
          <span className="ta-confidence-val">{result.confidence}%</span>
        </div>
        <p className="ta-summary">{result.summary}</p>
      </div>

      {/* Indicator grid */}
      <div className="ta-indicator-grid">
        <div className="ta-indicator-card">
          <h4>趋势</h4>
          <span className={`ta-badge ${result.indicators.trend.maAlignment === 'bullish' ? 'ta-bullish' : result.indicators.trend.maAlignment === 'bearish' ? 'ta-bearish' : 'ta-neutral'}`}>
            {result.indicators.trend.maAlignment === 'bullish' ? '多头' : result.indicators.trend.maAlignment === 'bearish' ? '空头' : '中性'}
          </span>
          <p className="ta-detail">{result.indicators.trend.detail}</p>
        </div>
        <div className="ta-indicator-card">
          <h4>MACD</h4>
          <span className={`ta-badge ${result.indicators.momentum.macd.status === 'bullish' ? 'ta-bullish' : result.indicators.momentum.macd.status === 'bearish' ? 'ta-bearish' : 'ta-neutral'}`}>
            {result.indicators.momentum.macd.status === 'bullish' ? '多头' : result.indicators.momentum.macd.status === 'bearish' ? '空头' : '中性'}
          </span>
          <p className="ta-detail">{result.indicators.momentum.macd.detail}</p>
        </div>
        <div className="ta-indicator-card">
          <h4>RSI</h4>
          <span className={`ta-badge ${result.indicators.momentum.rsi.status === 'oversold' ? 'ta-bullish' : result.indicators.momentum.rsi.status === 'overbought' ? 'ta-bearish' : 'ta-neutral'}`}>
            {result.indicators.momentum.rsi.value}
          </span>
          <p className="ta-detail">{result.indicators.momentum.rsi.detail}</p>
        </div>
        <div className="ta-indicator-card">
          <h4>布林带</h4>
          <span className={`ta-badge ${result.indicators.volatility.position === 'lower' ? 'ta-bullish' : result.indicators.volatility.position === 'upper' ? 'ta-bearish' : 'ta-neutral'}`}>
            {result.indicators.volatility.position === 'upper' ? '上轨' : result.indicators.volatility.position === 'lower' ? '下轨' : '中轨'}
          </span>
          <p className="ta-detail">{result.indicators.volatility.detail}</p>
        </div>
        <div className="ta-indicator-card">
          <h4>量能</h4>
          <span className={`ta-badge ${result.indicators.volume.priceVolumeConfirm && result.indicators.volume.volumeRatio > 1 ? 'ta-bullish' : !result.indicators.volume.priceVolumeConfirm ? 'ta-bearish' : 'ta-neutral'}`}>
            {result.indicators.volume.priceVolumeConfirm ? '配合' : '背离'}
          </span>
          <p className="ta-detail">{result.indicators.volume.detail}</p>
        </div>
        <div className="ta-indicator-card">
          <h4>支撑/压力</h4>
          <p className="ta-detail">{result.indicators.supportResistance.detail}</p>
          <div className="ta-sr-levels">
            <span>支撑: {result.indicators.supportResistance.nearestSupport}</span>
            <span>压力: {result.indicators.supportResistance.nearestResistance}</span>
          </div>
        </div>
      </div>

      {/* Evidence & Risk */}
      <div className="ta-evidence-risk">
        <div className="ta-evidence">
          <h4 className="ta-green">📌 看涨证据</h4>
          <ul>{result.keyEvidence.map((e, i) => <li key={i}>{e}</li>)}</ul>
        </div>
        <div className="ta-risk">
          <h4 className="ta-red">⚠️ 风险提示</h4>
          <ul>{result.riskWarning.map((r, i) => <li key={i}>{r}</li>)}</ul>
        </div>
      </div>
    </div>
  )
}
```

---

### 任务 8：前端 AnalysisHistoryPage

**文件：**
- 创建：`frontend/src/pages/AnalysisHistoryPage.tsx`

- [ ] **步骤 1：创建历史页面组件**

```typescript
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getAnalysisHistory } from '../api/client'
import type { TechnicalAnalysisResult } from '../types/api'

export default function AnalysisHistoryPage() {
  const nav = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [symbol, setSymbol] = useState(searchParams.get('symbol') || '')
  const [results, setResults] = useState<TechnicalAnalysisResult[]>([])
  const [stats, setStats] = useState<{ totalRecords: number; verifiedCount: number; correctCount: number; accuracy: number | null } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const sym = searchParams.get('symbol') || undefined
    getAnalysisHistory(sym)
      .then(res => {
        setResults(res.items)
        setStats(res.stats)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [searchParams])

  const handleSearch = () => {
    const params = new URLSearchParams()
    if (symbol) params.set('symbol', symbol)
    setSearchParams(params)
  }

  const dirMap: Record<string, string> = { UP: '↑ 看涨', DOWN: '↓ 看跌', SIDEWAYS: '→ 盘整' }

  return (
    <div className="page ta-page">
      <div className="toolbar">
        <button className="back-btn" onClick={() => nav('/')}>← 返回搜索</button>
      </div>
      <h2>技术研判历史</h2>

      {/* Search */}
      <div className="ta-search-bar">
        <input type="text" placeholder="输入股票代码筛选" value={symbol} onChange={e => setSymbol(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()} />
        <button onClick={handleSearch}>筛选</button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="ta-stats-bar">
          <span>总分析: {stats.totalRecords}</span>
          <span>已验证: {stats.verifiedCount}</span>
          <span>正确: {stats.correctCount}</span>
          <span>准确率: <b>{stats.accuracy != null ? `${stats.accuracy}%` : '--'}</b></span>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <p className="hint">加载中...</p>
      ) : results.length === 0 ? (
        <p className="hint">暂无分析记录</p>
      ) : (
        <table className="ta-history-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>股票</th>
              <th>方向</th>
              <th>信心</th>
              <th>当时价格</th>
              <th>结果</th>
            </tr>
          </thead>
          <tbody>
            {results.map(r => (
              <tr key={r.id} onClick={() => nav(`/analysis/${r.symbol}`)} className="ta-history-row">
                <td>{r.createdAt ? new Date(r.createdAt).toLocaleDateString('zh-CN') : ''}</td>
                <td>{r.symbol}<br /><span className="dim">{r.name}</span></td>
                <td><span className={`ta-dir-${r.direction.toLowerCase()}`}>{dirMap[r.direction] || r.direction}</span></td>
                <td>{r.confidence}%</td>
                <td>{r.priceAtAnalysis}</td>
                <td>
                  {r.isCorrect === true ? <span className="ta-correct">✓ 正确</span> : r.isCorrect === false ? <span className="ta-wrong">✗ 错误</span> : <span className="dim">待验证</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
```

---

### 任务 9：前端样式

**文件：**
- 创建：`frontend/src/styles/technical-analysis.css`

- [ ] **步骤 1：创建样式文件**

```css
.ta-page { max-width: 900px; margin: 0 auto; }
.ta-header { margin-bottom: 16px; }
.ta-header h2 { margin: 0; font-size: 1.3rem; }

.ta-direction-card {
  padding: 20px; border-radius: 10px; margin-bottom: 20px;
  border: 1px solid #e0e0e0;
}
.ta-direction-card.ta-up { background: #f0fff4; border-color: #b7eb8f; }
.ta-direction-card.ta-down { background: #fff1f0; border-color: #ffccc7; }
.ta-direction-card.ta-sideways { background: #fafafa; border-color: #d9d9d9; }

.ta-direction-badge {
  font-size: 1.8rem; font-weight: bold; margin-bottom: 12px;
}
.ta-up .ta-direction-badge { color: #52c41a; }
.ta-down .ta-direction-badge { color: #ff4d4f; }
.ta-sideways .ta-direction-badge { color: #8c8c8c; }

.ta-confidence-section { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.ta-confidence-label { font-size: 0.85rem; color: #666; white-space: nowrap; }
.ta-confidence-bar-wrap { flex: 1; height: 12px; background: #f0f0f0; border-radius: 6px; overflow: hidden; }
.ta-confidence-bar { height: 100%; background: linear-gradient(90deg, #52c41a, #faad14, #ff4d4f); border-radius: 6px; transition: width 0.5s; }
.ta-confidence-val { font-size: 1rem; font-weight: bold; min-width: 40px; }

.ta-summary { font-size: 0.9rem; color: #333; line-height: 1.6; }

.ta-indicator-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px; }
@media (max-width: 600px) { .ta-indicator-grid { grid-template-columns: repeat(2, 1fr); } }

.ta-indicator-card {
  padding: 14px; border-radius: 8px; border: 1px solid #f0f0f0; background: #fafafa;
}
.ta-indicator-card h4 { margin: 0 0 8px; font-size: 0.9rem; color: #333; }
.ta-badge {
  display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 0.8rem; font-weight: bold;
}
.ta-bullish { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
.ta-bearish { background: #fff2f0; color: #ff4d4f; border: 1px solid #ffccc7; }
.ta-neutral { background: #fafafa; color: #8c8c8c; border: 1px solid #d9d9d9; }
.ta-detail { font-size: 0.8rem; color: #555; margin: 6px 0 0; line-height: 1.5; }
.ta-sr-levels { display: flex; gap: 12px; margin-top: 6px; font-size: 0.8rem; color: #555; }

.ta-evidence-risk { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
@media (max-width: 600px) { .ta-evidence-risk { grid-template-columns: 1fr; } }
.ta-evidence, .ta-risk { padding: 14px; border-radius: 8px; border: 1px solid #e0e0e0; }
.ta-evidence { background: #f6ffed; }
.ta-risk { background: #fff2f0; }
.ta-green { color: #52c41a; margin: 0 0 8px; }
.ta-red { color: #ff4d4f; margin: 0 0 8px; }
.ta-evidence ul, .ta-risk ul { margin: 0; padding-left: 18px; font-size: 0.85rem; line-height: 1.8; }

.ta-dir-up { color: #52c41a; font-weight: bold; }
.ta-dir-down { color: #ff4d4f; font-weight: bold; }
.ta-dir-sideways { color: #8c8c8c; font-weight: bold; }
.ta-correct { color: #52c41a; font-weight: bold; }
.ta-wrong { color: #ff4d4f; font-weight: bold; }
.ta-history-row { cursor: pointer; }
.ta-history-row:hover { background: #f5f5f5; }

.ta-search-bar { display: flex; gap: 8px; margin-bottom: 16px; }
.ta-search-bar input { flex: 1; padding: 8px 12px; border: 1px solid #d9d9d9; border-radius: 6px; }
.ta-search-bar button { padding: 8px 20px; background: #1677ff; color: #fff; border: none; border-radius: 6px; cursor: pointer; }

.ta-stats-bar { display: flex; gap: 20px; padding: 12px 16px; background: #fafafa; border-radius: 8px; margin-bottom: 16px; font-size: 0.9rem; }

.ta-history-table { width: 100%; border-collapse: collapse; }
.ta-history-table th, .ta-history-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #f0f0f0; font-size: 0.85rem; }
.ta-history-table th { background: #fafafa; font-weight: 600; color: #333; }
```

---

### 任务 10：前端 Wiring

**文件：**
- 修改：`frontend/src/App.tsx`
- 修改：`frontend/src/pages/DetailPage.tsx`
- 修改：`frontend/src/index.css`
- 修改：`frontend/src/api/client.ts`（更新 import）

- [ ] **步骤 1：添加路由**

修改 `frontend/src/App.tsx`：

```typescript
import TechnicalAnalysisPage from './pages/TechnicalAnalysisPage'
import AnalysisHistoryPage from './pages/AnalysisHistoryPage'
```

在 `<Route path="/stock/:symbol" element={<DetailPage />} />` 之后添加：

```typescript
<Route path="/analysis/:symbol" element={<TechnicalAnalysisPage />} />
<Route path="/analysis/history" element={<AnalysisHistoryPage />} />
```

- [ ] **步骤 2：详情页添加入口按钮**

在 `frontend/src/pages/DetailPage.tsx` 的工具栏中，「刷新数据」按钮旁添加：

```typescript
<button className="collect-btn" onClick={() => nav(`/analysis/${symbol}`)}>技术研判</button>
```

确保 `useNavigate` 已在文件顶部导入（`import { useParams, useNavigate } from 'react-router-dom'`，已包含 `useNavigate`）。

- [ ] **步骤 3：更新 client.ts import**

修改 `frontend/src/api/client.ts` 顶部 import 行：

```typescript
import type { StockItem, StockQuote, AnalysisResult, WatchlistItem, TAnalysisResult, KlineBar, NewsItem, TechnicalAnalysisResult, AnalysisHistoryResponse } from '../types/api'
```

- [ ] **步骤 4：引入样式**

在 `frontend/src/index.css` 文件末尾添加：

```css
@import './styles/technical-analysis.css';
```

- [ ] **步骤 5：构建验证**

运行：`npm run build`
预期输出：构建成功，无错误

---

### 完整验证

- [ ] **步骤 1：启动后端**

运行：`python -m uvicorn src.main:app --port 8008`
确认服务启动无异常。

- [ ] **步骤 2：启动前端**

运行：`npm run dev`
确认前端启动正常。

- [ ] **步骤 3：端到端测试**

用 Playwright 或 curl 验证：
```bash
curl.exe http://localhost:8008/api/stocks/600519/technical-analysis
```
预期：返回完整的技术分析 JSON 结构。

- [ ] **步骤 4：页面渲染测试**

访问 `http://localhost:5173/analysis/600519`，确认页面正常渲染，方向标识 + 指标卡片显示正常。

- [ ] **步骤 5：历史页面测试**

访问 `http://localhost:5173/analysis/history`，确认历史记录页面正常。
