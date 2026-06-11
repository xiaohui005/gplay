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

    indicators = dict(result["indicators"])
    indicators["_keyEvidence"] = result["keyEvidence"]
    indicators["_riskWarning"] = result["riskWarning"]
    indicators["_recommendation"] = result["recommendation"]
    indicators["_signals"] = result["signals"]

    record = TechnicalRecord(
        symbol=symbol,
        name=basic.name,
        price_at_analysis=latest_close,
        predicted_direction=result["direction"],
        confidence_score=result["confidence"],
        indicators_json=json.dumps(indicators, ensure_ascii=False),
        summary=result["summary"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return record.to_dict()


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
