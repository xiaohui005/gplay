import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.models import UserWatchlist, StockBasic, StockQuoteSnapshot

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
def get_watchlist(db: Session = Depends(get_db)):
    rows = db.query(UserWatchlist).order_by(UserWatchlist.added_at.desc()).all()
    items = []
    for r in rows:
        basic = db.query(StockBasic).filter(StockBasic.symbol == r.symbol).first()
        q = db.query(StockQuoteSnapshot).filter(
            StockQuoteSnapshot.symbol == r.symbol
        ).order_by(StockQuoteSnapshot.id.desc()).first()
        items.append({
            "symbol": r.symbol,
            "name": basic.name if basic else r.symbol,
            "market": basic.market if basic else "",
            "latestPrice": q.latest_price if q else None,
            "changePercent": q.change_percent if q else None,
            "addedAt": r.added_at.isoformat() if r.added_at else None,
        })
    return {"items": items}


@router.post("/{symbol}")
def add_watchlist(symbol: str, db: Session = Depends(get_db)):
    exist = db.query(UserWatchlist).filter(UserWatchlist.symbol == symbol).first()
    if exist:
        return {"status": "ok", "symbol": symbol, "message": "已在关注列表中"}
    basic = db.query(StockBasic).filter(StockBasic.symbol == symbol).first()
    if not basic:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 不存在，请先采集")
    db.add(UserWatchlist(symbol=symbol, added_at=datetime.datetime.now(datetime.timezone.utc)))
    db.commit()
    return {"status": "ok", "symbol": symbol, "message": "关注成功"}


@router.delete("/{symbol}")
def remove_watchlist(symbol: str, db: Session = Depends(get_db)):
    row = db.query(UserWatchlist).filter(UserWatchlist.symbol == symbol).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 不在关注列表中")
    db.delete(row)
    db.commit()
    return {"status": "ok", "symbol": symbol, "message": "已取消关注"}
