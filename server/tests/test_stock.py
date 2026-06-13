import datetime

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.models.stock_basic import StockBasic
from src.models.stock_kline_daily import StockKlineDaily
from src.models.stock_news import StockNews
from src.models.stock_quote_snapshot import StockQuoteSnapshot
from src.db.database import SessionLocal, engine, Base

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _seed_stock_basic():
    session = SessionLocal()
    try:
        stocks = [
            StockBasic(symbol="600000", name="浦发银行", market="SSE", trade_status="TRADING", pinyin="pfyh"),
            StockBasic(symbol="000001", name="平安银行", market="SZSE", trade_status="TRADING", pinyin="payh"),
            StockBasic(symbol="600519", name="贵州茅台", market="SSE", trade_status="TRADING", pinyin="gzmt"),
            StockBasic(symbol="000002", name="万科A", market="SZSE", trade_status="SUSPENDED", pinyin="wka"),
            StockBasic(symbol="300999", name="金龙鱼", market="SZSE", trade_status="DELISTED", pinyin="jly"),
        ]
        for s in stocks:
            session.add(s)
        session.commit()
    finally:
        session.close()


def _seed_stock_quote():
    session = SessionLocal()
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        quotes = [
            StockQuoteSnapshot(symbol="600000", latest_price=8.25, change_percent=2.5, volume=1.2e8, amount=9.9e8, turnover_rate=0.85, volume_ratio=1.35, data_time=now, delay_minutes=15, quote_type="REALTIME"),
            StockQuoteSnapshot(symbol="000001", latest_price=12.30, change_percent=-0.8, volume=5e7, amount=6.15e8, turnover_rate=0.62, volume_ratio=0.75, data_time=now, delay_minutes=0, quote_type="REALTIME"),
            StockQuoteSnapshot(symbol="600519", latest_price=1880.00, change_percent=3.2, volume=3e6, amount=5.64e9, turnover_rate=0.28, volume_ratio=1.82, data_time=now, delay_minutes=15, quote_type="REALTIME"),
            StockQuoteSnapshot(symbol="000002", latest_price=9.15, change_percent=-1.5, volume=2e7, amount=1.83e8, turnover_rate=0.35, volume_ratio=0.50, data_time=now, delay_minutes=0, quote_type="REALTIME"),
        ]
        for q in quotes:
            session.add(q)
        session.commit()
    finally:
        session.close()


class TestStockSearch:
    def test_search_by_symbol_prefix(self):
        _seed_stock_basic()
        resp = client.get("/api/stocks/search", params={"keyword": "600"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1
        symbols = {i["symbol"] for i in data["items"]}
        assert "600000" in symbols
        assert "600519" in symbols

    def test_search_by_name(self):
        _seed_stock_basic()
        resp = client.get("/api/stocks/search", params={"keyword": "银行"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1
        names = {i["name"] for i in data["items"]}
        assert "浦发银行" in names

    def test_search_by_pinyin(self):
        _seed_stock_basic()
        resp = client.get("/api/stocks/search", params={"keyword": "pfyh"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["symbol"] == "600000"

    def test_search_with_quote_data(self):
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/search", params={"keyword": "600000"})
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["latestPrice"] == 8.25
        assert item["changePercent"] == 2.5
        assert item["tradeStatus"] == "TRADING"

    def test_search_no_result(self):
        _seed_stock_basic()
        resp = client.get("/api/stocks/search", params={"keyword": "ZZZZZZ"})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 0

    def test_search_empty_keyword(self):
        resp = client.get("/api/stocks/search", params={"keyword": ""})
        assert resp.status_code == 422

    def test_search_limit(self):
        _seed_stock_basic()
        resp = client.get("/api/stocks/search", params={"keyword": "0", "limit": 2})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 2


class TestStockQuote:
    def test_get_quote(self):
        _seed_stock_quote()
        resp = client.get("/api/stocks/600000/quote")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "600000"
        assert data["latestPrice"] == 8.25

    def test_get_quote_not_found(self):
        _seed_stock_quote()
        resp = client.get("/api/stocks/999999/quote")
        assert resp.status_code == 404


class TestStockNewsCollect:
    def test_collect_news_only_does_not_collect_quote_or_kline(self, monkeypatch):
        def fake_fetch_news(symbol):
            return [{
                "title": "浦发银行发布经营动态",
                "source": "东方财富",
                "publish_time": "2026-06-14 10:00:00",
                "url": "https://example.com/news/1",
                "content_summary": "仅用于测试的新闻摘要",
            }]

        monkeypatch.setattr("src.handlers.stock.fetch_news", fake_fetch_news)

        resp = client.post("/api/stocks/600000/collect-news")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["symbol"] == "600000"
        assert data["newsCount"] == 1

        session = SessionLocal()
        try:
            assert session.query(StockNews).filter(StockNews.symbol == "600000").count() == 1
            assert session.query(StockQuoteSnapshot).filter(StockQuoteSnapshot.symbol == "600000").count() == 0
            assert session.query(StockKlineDaily).filter(StockKlineDaily.symbol == "600000").count() == 0
        finally:
            session.close()


class TestStockAnalysis:
    def test_analysis_basic(self):
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/600000/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "600000"
        assert data["market"] == "SSE"
        assert data["dataTime"] is not None
        assert isinstance(data["delayMinutes"], int)
        assert data["delayMinutes"] == 15
        assert data["trendStatus"] in (
            "STRONG_UPTREND", "WEAK_UPTREND", "RANGE_BOUND",
            "WEAK_DOWN_TREND", "DOWN_TREND",
        )
        assert data["riskLevel"] in ("LOW", "MEDIUM", "HIGH", "EXTREME")
        assert data["suggestion"] in ("BUY_WATCH", "BUY_LIGHT", "HOLD", "REDUCE", "SELL", "AVOID")

    def test_analysis_score_fields(self):
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/600000/analysis")
        assert resp.status_code == 200
        s = resp.json()["score"]
        for k in ("total", "trend", "volumePrice", "sector", "fundamental", "riskPenalty"):
            assert k in s
        assert 0 <= s["total"] <= 100
        assert 0 <= s["trend"] <= 100

    def test_analysis_master_guidance(self):
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/600000/analysis")
        assert resp.status_code == 200
        mg = resp.json()["masterGuidance"]
        assert isinstance(mg["summary"], str)
        assert isinstance(mg["upsideConditions"], list)
        assert isinstance(mg["pullbackConditions"], list)
        assert isinstance(mg["buyPlan"], list)
        assert isinstance(mg["sellPlan"], list)
        assert isinstance(mg["reviewPoints"], list)

    def test_analysis_disclaimer(self):
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/600000/analysis")
        assert "disclaimer" in resp.json()
        assert "仅供参考" in resp.json()["disclaimer"]

    def test_analysis_suspended_stock(self):
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/000002/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "000002"
        assert data["riskLevel"] in ("HIGH", "EXTREME")

    def test_analysis_delisted_stock(self):
        _seed_stock_basic()
        resp = client.get("/api/stocks/300999/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["riskLevel"] == "EXTREME"
        assert data["suggestion"] == "AVOID"

    def test_analysis_not_found(self):
        resp = client.get("/api/stocks/999999/analysis")
        assert resp.status_code == 404

    def test_analysis_no_quote_present(self):
        _seed_stock_basic()
        resp = client.get("/api/stocks/600000/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["delayMinutes"] == 0
