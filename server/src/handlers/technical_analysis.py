import datetime
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.analysis.technical_engine import analyze_technical
from src.data_sources.east_money import fetch_kline
from src.data_sources.tencent_quote import fetch_quote
from src.db.database import get_db
from src.models import StockBasic, TechnicalRecord, StockQuoteSnapshot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stocks", tags=["technical-analysis"])


@router.get("/{symbol}/technical-analysis")
def get_technical_analysis(symbol: str, db: Session = Depends(get_db)):
    basic = db.query(StockBasic).filter(StockBasic.symbol == symbol).first()
    if not basic:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 未找到")

    return _build_technical_analysis(symbol, basic)


@router.post("/{symbol}/technical-analysis")
def save_technical_analysis(symbol: str, db: Session = Depends(get_db)):
    return save_technical_analysis_for_symbol(db, symbol)


def save_technical_analysis_for_symbol(db: Session, symbol: str, allow_duplicate: bool = False):
    basic = db.query(StockBasic).filter(StockBasic.symbol == symbol).first()
    if not basic:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 未找到")

    payload = _build_technical_analysis(symbol, basic)
    indicators = _build_record_indicators(payload)

    existing_record = None if allow_duplicate else _find_today_session_record(db, symbol, payload["analysisSession"])
    if existing_record:
        existing_record.name = basic.name
        existing_record.price_at_analysis = payload["priceAtAnalysis"]
        existing_record.predicted_direction = payload["direction"]
        existing_record.confidence_score = payload["confidence"]
        existing_record.indicators_json = json.dumps(indicators, ensure_ascii=False)
        existing_record.summary = payload["summary"]
        existing_record.created_at = datetime.datetime.now()
        db.commit()
        db.refresh(existing_record)
        return existing_record.to_dict()

    record = TechnicalRecord(
        symbol=symbol,
        name=basic.name,
        price_at_analysis=payload["priceAtAnalysis"],
        predicted_direction=payload["direction"],
        confidence_score=payload["confidence"],
        indicators_json=json.dumps(indicators, ensure_ascii=False),
        summary=payload["summary"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return record.to_dict()


def _build_record_indicators(payload: dict) -> dict:
    indicators = dict(payload["indicators"])
    indicators["_keyEvidence"] = payload["keyEvidence"]
    indicators["_riskWarning"] = payload["riskWarning"]
    indicators["_recommendation"] = payload["recommendation"]
    indicators["_signals"] = payload["signals"]
    indicators["_analysisSession"] = payload["analysisSession"]
    indicators["_analysisTimeLabel"] = payload["analysisTimeLabel"]
    return indicators


def _find_today_session_record(db: Session, symbol: str, analysis_session: str):
    today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    records = db.query(TechnicalRecord).filter(
        TechnicalRecord.symbol == symbol,
        TechnicalRecord.created_at >= today_start,
    ).order_by(TechnicalRecord.created_at.desc()).all()
    for record in records:
        data = record.to_dict()
        existing_session = data.get("analysisSession") or _infer_analysis_session(record.created_at)
        if existing_session == analysis_session:
            return record
    return None


def _build_technical_analysis(symbol: str, basic: StockBasic):

    klines = sorted(fetch_kline(symbol, datalen=120), key=lambda k: k.get("date", ""))
    if not klines:
        raise HTTPException(status_code=400, detail=f"股票 {symbol} K线数据获取失败")
    klines = _merge_live_quote_into_klines(symbol, klines)

    current_price = klines[-1].get("close") if klines[-1].get("close") is not None else None
    if current_price is None:
        raise HTTPException(status_code=400, detail=f"股票 {symbol} 无有效收盘价")

    result = analyze_technical(klines)

    # Compute buy/sell/stop based on current price + ATR
    atr = result.get("indicators", {}).get("volatility", {}).get("width", 0)
    atr_price = current_price * atr / 100 if atr else current_price * 0.02
    direction = result["direction"]
    if direction == "UP":
        signals = {"buyPrice": round(current_price, 2), "sellPrice": round(current_price + atr_price, 2), "stopLoss": round(current_price - atr_price * 0.5, 2)}
    elif direction == "DOWN":
        signals = {"buyPrice": round(current_price - atr_price * 0.5, 2), "sellPrice": round(current_price, 2), "stopLoss": round(current_price + atr_price * 0.5, 2)}
    else:
        signals = {"buyPrice": round(current_price - atr_price * 0.3, 2), "sellPrice": round(current_price + atr_price * 0.3, 2), "stopLoss": round(current_price - atr_price * 0.8, 2)}
    if direction == "UP":
        signals["stopLoss"] = min(signals["stopLoss"], round(signals["buyPrice"] * 0.97, 2))
        signals["sellPrice"] = max(signals["sellPrice"], round(signals["buyPrice"] * 1.005, 2))
    elif direction == "DOWN":
        signals["stopLoss"] = max(signals["stopLoss"], round(signals["sellPrice"] * 1.03, 2))
        signals["buyPrice"] = min(signals["buyPrice"], round(signals["sellPrice"] * 0.995, 2))

    analysis_session, analysis_time_label = _get_analysis_session(datetime.datetime.now())

    return {
        "id": None,
        "symbol": symbol,
        "name": basic.name,
        "createdAt": None,
        "priceAtAnalysis": current_price,
        "direction": result["direction"],
        "confidence": result["confidence"],
        "recommendation": result["recommendation"],
        "signals": signals,
        "indicators": result["indicators"],
        "keyEvidence": result["keyEvidence"],
        "riskWarning": result["riskWarning"],
        "summary": result["summary"],
        "isCorrect": None,
        "actualDirection": None,
        "verifiedAt": None,
        "analysisSession": analysis_session,
        "analysisTimeLabel": analysis_time_label,
    }


def _merge_live_quote_into_klines(symbol: str, klines: list[dict]) -> list[dict]:
    try:
        quote = fetch_quote(symbol)
    except Exception as exc:
        logger.warning("获取实时行情失败，使用日K数据研判 [%s]: %s", symbol, exc)
        return klines

    latest_price = quote.get("latest_price")
    quote_time = quote.get("datetime_str") or ""
    if not latest_price or len(quote_time) < 8:
        return klines

    quote_date = datetime.datetime.strptime(quote_time[:8], "%Y%m%d").date().isoformat()
    live_row = {
        "date": quote_date,
        "open": quote.get("open") or latest_price,
        "close": latest_price,
        "high": quote.get("high") or latest_price,
        "low": quote.get("low") or latest_price,
        "volume": quote.get("volume") or 0,
        "amount": quote.get("amount"),
    }

    rows = list(klines)
    if rows and rows[-1].get("date") == quote_date:
        rows[-1] = {**rows[-1], **live_row}
    else:
        rows.append(live_row)
    return sorted(rows, key=lambda k: k.get("date", ""))


def _get_analysis_session(now: datetime.datetime):
    if now.time() < datetime.time(12, 0):
        return "MORNING", f"{now:%Y/%m/%d} 早盘研判 10:00"
    return "AFTERNOON", f"{now:%Y/%m/%d} 收盘前研判 14:30"


def _infer_analysis_session(created_at: datetime.datetime | None):
    if not created_at:
        return None
    return "MORNING" if created_at.time() < datetime.time(12, 0) else "AFTERNOON"


def evaluate_prediction(predicted_direction: str, change_pct: float) -> dict:
    actual = "UP" if change_pct >= 0 else "DOWN"
    return {"actualDirection": actual, "isCorrect": actual == predicted_direction}


def normalize_prediction_result(predicted_direction: str, actual_direction: str | None, is_correct: bool | None) -> dict:
    if actual_direction == "SIDEWAYS":
        if is_correct is True:
            actual_direction = predicted_direction
        elif predicted_direction == "UP":
            actual_direction = "DOWN"
        else:
            actual_direction = "UP"
        is_correct = actual_direction == predicted_direction
    return {"actualDirection": actual_direction, "isCorrect": is_correct}


def select_validation_price(created_at: datetime.datetime, analysis_session: str | None, klines: list[dict]) -> float | None:
    rows = sorted(klines, key=lambda k: k.get("date", ""))
    created_date = created_at.date().isoformat()
    session = analysis_session or _infer_analysis_session(created_at)
    if session == "MORNING":
        for row in rows:
            if row.get("date") == created_date:
                return row.get("close")
        return None
    return None


def select_intraday_validation_price(created_at: datetime.datetime, analysis_session: str | None, snapshots: list[StockQuoteSnapshot]) -> float | None:
    session = analysis_session or _infer_analysis_session(created_at)
    if session != "AFTERNOON":
        return None
    target_date = created_at.date() + datetime.timedelta(days=1)
    target_start = datetime.datetime.combine(target_date, datetime.time(10, 0))
    tolerance_start = target_start - datetime.timedelta(minutes=5)
    rows = sorted(
        (s for s in snapshots if s.data_time and s.data_time >= target_start and s.latest_price is not None),
        key=lambda s: s.data_time,
    )
    if rows:
        return rows[0].latest_price
    fallback_rows = sorted(
        (s for s in snapshots if s.data_time and tolerance_start <= s.data_time < target_start and s.latest_price is not None),
        key=lambda s: s.data_time,
        reverse=True,
    )
    return fallback_rows[0].latest_price if fallback_rows else None


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

    now = datetime.datetime.now()
    for rec in records:
        normalized = normalize_prediction_result(rec.predicted_direction, rec.actual_direction, rec.is_correct)
        if normalized["isCorrect"] != rec.is_correct:
            rec.is_correct = normalized["isCorrect"]
            db.commit()
        if rec.is_correct is not None:
            continue
        if rec.created_at and (now - rec.created_at).total_seconds() < 3600:
            continue
        analysis_session = rec.to_dict().get("analysisSession")
        validation_price = select_intraday_validation_price(
            rec.created_at,
            analysis_session,
            db.query(StockQuoteSnapshot).filter(StockQuoteSnapshot.symbol == rec.symbol).all(),
        )
        if validation_price is None:
            klines = fetch_kline(rec.symbol, datalen=5)
            validation_price = select_validation_price(rec.created_at, analysis_session, klines)
        if validation_price is None:
            continue
        change_pct = (validation_price - rec.price_at_analysis) / rec.price_at_analysis * 100
        result = evaluate_prediction(rec.predicted_direction, change_pct)
        rec.actual_direction = result["actualDirection"]
        rec.is_correct = result["isCorrect"]
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
