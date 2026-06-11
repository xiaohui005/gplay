import datetime

from src.db.database import SessionLocal, engine
from src.db.migrations import run_migrations
from src.models import StockBasic, StockQuoteSnapshot
from src.analysis.strategy_config import create_default_strategy

STOCKS = [
    # (symbol, name, market, trade_status, pinyin, list_date, total_shares, price, change_pct, vol_ratio, delay)
    ("600000", "浦发银行", "SSE", "TRADING",  "pfyh",  "1999-11-10", 293.5,  8.52,  +0.35, 1.2, 0),
    ("600036", "招商银行", "SSE", "TRADING",  "zsyh",  "2002-04-09", 252.2,  36.18, +1.28, 1.5, 0),
    ("000001", "平安银行", "SZSE", "TRADING", "payh",  "1991-04-03", 194.0,  11.24, -0.62, 0.8, 0),
    ("600519", "贵州茅台", "SSE", "TRADING",  "gzmt",  "2001-08-27", 12.56, 1680.00,+2.15, 2.1, 0),
    ("000858", "五粮液",   "SZSE", "TRADING", "wly",   "1998-04-27", 38.82, 148.30, +0.88, 1.3, 0),
    ("002415", "海康威视", "SZSE", "TRADING", "hkws",  "2010-05-28", 93.32, 32.50,  -0.45, 0.7, 0),
    ("600276", "恒瑞医药", "SSE", "TRADING",  "hryy",  "2000-10-18", 63.78, 46.80,  +1.05, 1.1, 0),
    ("300750", "宁德时代", "SZSE", "TRADING", "ndsd",  "2018-06-11", 44.0,  195.60, +3.20, 2.5, 0),
    ("601857", "中国石油", "SSE", "TRADING",  "zgsy",  "2007-11-05", 1830.2, 8.15,  -0.12, 0.5, 0),
    ("600030", "中信证券", "SSE", "TRADING",  "zxzq",  "2003-01-06", 148.0,  20.35, +1.50, 1.8, 0),
    ("601318", "中国平安", "SSE", "TRADING",  "zgpa",  "2007-03-01", 182.8,  52.40, +0.60, 0.9, 0),
    ("600104", "上汽集团", "SSE", "TRADING",  "sqjt",  "1997-11-25", 116.8,  14.22, -0.28, 0.6, 0),
    ("000002", "万科A",    "SZSE", "TRADING", "wk",    "1991-01-29", 119.3,  9.85,   -1.50, 0.4, 0),
    ("600600", "青岛啤酒", "SSE", "TRADING",  "qdpj",  "1993-08-27", 13.64, 68.90,  +0.72, 1.0, 0),
]

SUSPENDED = ("000007", "全新好", "SZSE", "SUSPENDED", "qxh", "1986-06-30", 3.46)
ST_STOCK = ("002872", "ST天圣", "SZSE", "TRADING", "stts", "2011-12-05", 3.18, 5.20, -2.80, 0.3, 0)

NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def seed():
    run_migrations()

    session = SessionLocal()
    try:
        create_default_strategy(session)
        existing = session.query(StockBasic).count()
        if existing > 0:
            print(f"数据库已有 {existing} 条股票记录，跳过种子数据")
            return

        for row in STOCKS:
            symbol, name, market, status, pinyin, list_date, shares = row[:7]
            price, change_pct, vol_ratio, delay = row[7:11] if len(row) > 7 else (None, None, None, 0)
            sb = StockBasic(
                symbol=symbol, name=name, market=market,
                trade_status=status, pinyin=pinyin,
                list_date=list_date, total_shares=shares,
            )
            session.add(sb)

            if price is not None:
                q = StockQuoteSnapshot(
                    symbol=symbol,
                    latest_price=price,
                    change_percent=change_pct,
                    volume=int(abs(price * 1e6)),
                    amount=int(abs(price * 1e8)),
                    turnover_rate=round(abs(change_pct or 0) * 0.5 + 0.5, 2),
                    volume_ratio=vol_ratio,
                    high=round(price * (1 + abs(change_pct or 0) / 200), 2),
                    low=round(price * (1 - abs(change_pct or 0) / 200), 2),
                    open_price=round(price * (1 - abs(change_pct or 0) / 400), 2),
                    pre_close=price,
                    amplitude=round(abs(change_pct or 0) * 0.8, 2),
                    data_time=NOW,
                    delay_minutes=delay,
                    quote_type="DELAYED" if delay > 0 else "REALTIME",
                )
                session.add(q)

        # suspended stock
        sym, name, mkt, sts, pyn, ld, ts = SUSPENDED
        session.add(StockBasic(symbol=sym, name=name, market=mkt, trade_status=sts, pinyin=pyn, list_date=ld, total_shares=ts))

        # ST stock
        sym, name, mkt, sts, pyn, ld, ts, price, cp, vr, delay = ST_STOCK
        session.add(StockBasic(symbol=sym, name=name, market=mkt, trade_status=sts, pinyin=pyn, list_date=ld, total_shares=ts))
        q = StockQuoteSnapshot(symbol=sym, latest_price=price, change_percent=cp, volume=500000, amount=2600000,
                               turnover_rate=1.2, volume_ratio=vr, high=round(price * 1.05, 2),
                               low=round(price * 0.95, 2), open_price=round(price * 0.98, 2),
                               pre_close=round(price / (1 + cp / 100), 2), amplitude=5.5,
                               data_time=NOW, delay_minutes=0, quote_type="REALTIME")
        session.add(q)

        # delayed quote for 600000 (150min delay)
        session.add(StockQuoteSnapshot(symbol="600000", latest_price=8.50, change_percent=0.12, volume=500000,
                                        amount=4250000, turnover_rate=0.15, volume_ratio=0.6,
                                        high=8.55, low=8.48, open_price=8.52, pre_close=8.49, amplitude=0.82,
                                        data_time=NOW, delay_minutes=150, quote_type="DELAYED"))

        session.commit()
        count = session.query(StockBasic).count()
        qcount = session.query(StockQuoteSnapshot).count()
        print(f"种子数据写入完成: {count} 只股票, {qcount} 条行情")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
