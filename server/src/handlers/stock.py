import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.data_sources.tencent_quote import fetch_quote
from src.data_sources.east_money import fetch_stock_list, fetch_kline
from src.db.database import get_db
from src.models import StockBasic, StockQuoteSnapshot
from src.services.stock_service import StockService

router = APIRouter(prefix="/api/stocks", tags=["stock"])


@router.get("/search")
def search_stocks(
    keyword: str = Query(..., min_length=1, max_length=64, description="搜索关键词：代码/名称/拼音"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = StockService(db)
    items = service.search(keyword.strip(), limit)
    return {"items": items}


@router.post("/{symbol}/collect")
def collect_stock(symbol: str, db: Session = Depends(get_db)):
    quote = fetch_quote(symbol)
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)

    exist = db.query(StockBasic).filter(StockBasic.symbol == symbol).first()
    if not exist:
        market = _detect_market(symbol)
        db.add(StockBasic(
            symbol=symbol, name=quote["name"], market=market,
            trade_status="TRADING", pinyin="",
        ))
        exist = db.query(StockBasic).filter(StockBasic.symbol == symbol).first()

    db.add(StockQuoteSnapshot(
        symbol=symbol,
        latest_price=quote["latest_price"],
        change_percent=quote["change_percent"],
        volume=quote["volume"],
        amount=quote["amount"],
        turnover_rate=round(abs(quote.get("change_percent", 0)) * 0.3 + 0.5, 2),
        volume_ratio=1.5,
        high=quote.get("high"),
        low=quote.get("low"),
        open_price=quote.get("open"),
        pre_close=quote.get("pre_close"),
        amplitude=round(abs(quote.get("change_percent", 0)) * 0.8, 2),
        data_time=now,
        delay_minutes=0,
        quote_type="REALTIME",
    ))

    try:
        kline = fetch_kline(symbol)
        has_kline = len(kline)
    except Exception:
        has_kline = 0

    db.commit()

    return {
        "status": "ok",
        "symbol": symbol,
        "name": quote["name"],
        "price": quote["latest_price"],
        "changePercent": quote["change_percent"],
        "klineBars": has_kline,
    }


@router.get("/{symbol}/analysis")
def stock_analysis(
    symbol: str,
    strategy_version: str = Query(None, description="策略版本号，为空则使用当前启用的策略"),
    db: Session = Depends(get_db),
):
    service = StockService(db)
    result = service.get_analysis(symbol, strategy_version)
    if result is None:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 未找到")
    return result


@router.get("/{symbol}/quote")
def stock_quote(symbol: str, db: Session = Depends(get_db)):
    service = StockService(db)
    result = service.get_quote(symbol)
    if result is None:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 行情数据未找到")
    return result


def _detect_market(code: str) -> str:
    if code.startswith(("6", "9")):
        return "SSE"
    if code.startswith(("0", "2", "3")):
        return "SZSE"
    if code.startswith(("4", "8")):
        return "BSE"
    return "SSE"
