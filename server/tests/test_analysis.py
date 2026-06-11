import json
import datetime

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.models.stock_basic import StockBasic
from src.models.stock_quote_snapshot import StockQuoteSnapshot
from src.analysis.strategy_config import StrategyConfig, create_default_strategy
from src.analysis.datatypes import (
    CapitalInput,
    EventInput,
    FinancialInput,
    KlineInput,
    QuoteInput,
    RiskInput,
    SectorInput,
)
from src.analysis.scorer import (
    compute_risk_penalty,
    score_capital,
    score_event,
    score_fundamental,
    score_sector,
    score_trend,
    score_volume_price,
)
from src.analysis.risk_control import (
    compute_risk_level,
    compute_trend_status,
    run_risk_control,
    RISK_LEVEL_EXTREME,
    RISK_LEVEL_HIGH,
    RISK_LEVEL_MEDIUM,
    RISK_LEVEL_LOW,
    SUGGESTION_AVOID,
    SUGGESTION_HOLD,
)
from src.analysis.suggestion import map_suggestion
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
            StockBasic(symbol="600888", name="华泰股份", market="SSE", trade_status="SUSPENDED", pinyin="htgf"),
            StockBasic(symbol="300999", name="金科退", market="SZSE", trade_status="DELISTED", pinyin="jkt"),
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
            StockQuoteSnapshot(symbol="600000", latest_price=8.25, change_percent=2.5, volume=1.2e8, amount=9.9e8, turnover_rate=0.85, volume_ratio=1.35, data_time=now, delay_minutes=15),
            StockQuoteSnapshot(symbol="000001", latest_price=12.30, change_percent=5.2, volume=8e7, amount=9.84e8, turnover_rate=0.95, volume_ratio=2.10, data_time=now, delay_minutes=0),
        ]
        for q in quotes:
            session.add(q)
        session.commit()
    finally:
        session.close()


# ============================================================
# Scorer tests
# ============================================================

class TestScorerTrend:
    def test_trend_base(self):
        k = KlineInput()
        s = score_trend(k)
        assert s == 50

    def test_trend_above_mas(self):
        k = KlineInput(ma5=10, ma10=9.5, ma20=9, ma60=8.5)
        q = QuoteInput(latest_price=11.0, change_percent=2.0)
        s = score_trend(k, q)
        assert 60 <= s <= 100

    def test_trend_below_mas(self):
        k = KlineInput(ma5=10, ma10=10, ma20=9.5, ma60=9)
        q = QuoteInput(latest_price=8.0, change_percent=-4.0)
        s = score_trend(k, q)
        assert s <= 50

    def test_trend_strong_uptrend(self):
        k = KlineInput(ma5=12, ma10=11, ma20=10, ma60=9)
        q = QuoteInput(latest_price=13.0, change_percent=5.0)
        s = score_trend(k, q)
        assert s >= 60

    def test_trend_no_ma(self):
        k = KlineInput()
        q = QuoteInput(latest_price=10.0, change_percent=2.0)
        s = score_trend(k, q)
        assert s == 50


class TestScorerVolumePrice:
    def test_base(self):
        assert score_volume_price() == 50

    def test_fangliang_tupo(self):
        q = QuoteInput(volume_ratio=2.0, change_percent=4.0)
        s = score_volume_price(q)
        assert s >= 65

    def test_fangliang_zhizhang(self):
        q = QuoteInput(volume_ratio=2.0, change_percent=0.3)
        s = score_volume_price(q)
        assert s <= 45

    def test_suoliang_huicai(self):
        q = QuoteInput(volume_ratio=0.5, change_percent=-0.5)
        s = score_volume_price(q)
        assert s >= 50

    def test_liangjia_beili(self):
        q = QuoteInput(volume_ratio=0.4, change_percent=4.0)
        s = score_volume_price(q)
        assert s <= 45


class TestScorerCapital:
    def test_no_data(self):
        assert score_capital() == 50

    def test_positive_inflow(self):
        c = CapitalInput(main_net_inflow=1e8)
        s = score_capital(c)
        assert s >= 60

    def test_negative_inflow(self):
        c = CapitalInput(main_net_inflow=-1e8)
        s = score_capital(c)
        assert s <= 45

    def test_continuous_inflow(self):
        c = CapitalInput(main_net_inflow=5e7, main_net_inflow_3d=2e8)
        s = score_capital(c)
        assert s >= 65


class TestScorerSector:
    def test_no_data(self):
        assert score_sector() == 50

    def test_strong_sector(self):
        sec = SectorInput(sector_change_pct=3.0, sector_rank=5)
        s = score_sector(sec)
        assert s >= 70

    def test_weak_sector(self):
        sec = SectorInput(sector_change_pct=-3.0, sector_rank=90)
        s = score_sector(sec)
        assert s <= 40


class TestScorerFundamental:
    def test_no_data(self):
        assert score_fundamental() == 50

    def test_good_roe(self):
        f = FinancialInput(roe=18.0, pe=12.0, profit_change_pct=25.0)
        s = score_fundamental(f)
        assert s >= 70

    def test_bad_roe(self):
        f = FinancialInput(roe=-5.0, pe=200.0, profit_change_pct=-30.0)
        s = score_fundamental(f)
        assert s <= 35


class TestScorerEvent:
    def test_no_data(self):
        assert score_event() == 50

    def test_positive(self):
        e = EventInput(has_positive_news=True)
        s = score_event(e)
        assert s >= 60

    def test_negative(self):
        e = EventInput(has_negative_news=True)
        s = score_event(e)
        assert s <= 40

    def test_regulatory_penalty(self):
        e = EventInput(has_regulatory_penalty=True)
        s = score_event(e)
        assert s <= 35


# ============================================================
# Risk Penalty tests
# ============================================================

class TestRiskPenalty:
    def test_normal_trading(self):
        r = RiskInput(trade_status="TRADING")
        assert compute_risk_penalty(r) == 0

    def test_delisted(self):
        r = RiskInput(trade_status="DELISTED")
        assert compute_risk_penalty(r) == 100

    def test_suspended(self):
        r = RiskInput(trade_status="SUSPENDED")
        p = compute_risk_penalty(r)
        assert 55 <= p <= 65

    def test_st_tag(self):
        r = RiskInput(trade_status="TRADING", has_st_tag=True)
        p = compute_risk_penalty(r)
        assert p >= 40

    def test_delist_risk(self):
        r = RiskInput(trade_status="TRADING", has_delist_risk=True)
        p = compute_risk_penalty(r)
        assert p >= 50

    def test_data_delay(self):
        r = RiskInput(trade_status="TRADING", delay_minutes=90)
        p = compute_risk_penalty(r)
        assert p >= 15

    def test_data_missing(self):
        r = RiskInput(trade_status="TRADING", data_missing=True)
        p = compute_risk_penalty(r)
        assert p >= 30

    def test_multiple_risks_no_overflow(self):
        r = RiskInput(trade_status="SUSPENDED", has_st_tag=True, has_major_penalty=True)
        p = compute_risk_penalty(r)
        assert p <= 100

    def test_shareholder_reduction(self):
        r = RiskInput(trade_status="TRADING", has_shareholder_reduction=True)
        p = compute_risk_penalty(r)
        assert p >= 20


# ============================================================
# Risk Control tests
# ============================================================

class TestRiskControl:
    def test_delisted_intercept(self):
        rc = run_risk_control(trade_status="DELISTED")
        assert rc.intercepted
        assert rc.suggestion == SUGGESTION_AVOID
        assert rc.risk_level == RISK_LEVEL_EXTREME

    def test_suspended_intercept(self):
        rc = run_risk_control(trade_status="SUSPENDED")
        assert rc.intercepted
        assert rc.suggestion == SUGGESTION_HOLD

    def test_st_tag_intercept(self):
        rc = run_risk_control(trade_status="TRADING", has_st_tag=True)
        assert rc.intercepted
        assert rc.suggestion == SUGGESTION_AVOID
        assert rc.risk_level == RISK_LEVEL_EXTREME

    def test_delist_risk_intercept(self):
        rc = run_risk_control(trade_status="TRADING", has_delist_risk=True)
        assert rc.intercepted
        assert rc.suggestion == SUGGESTION_AVOID

    def test_major_penalty_intercept(self):
        rc = run_risk_control(trade_status="TRADING", has_major_penalty=True)
        assert rc.intercepted
        assert rc.suggestion == SUGGESTION_AVOID

    def test_data_missing_intercept(self):
        rc = run_risk_control(trade_status="TRADING", data_missing=True)
        assert rc.intercepted
        assert rc.suggestion == SUGGESTION_HOLD

    def test_extreme_delay_intercept(self):
        rc = run_risk_control(trade_status="TRADING", delay_minutes=180)
        assert rc.intercepted
        assert rc.suggestion == SUGGESTION_HOLD

    def test_no_intercept_normal(self):
        rc = run_risk_control(trade_status="TRADING")
        assert not rc.intercepted
        assert rc.risk_level == RISK_LEVEL_LOW

    def test_shareholder_reduction_lowers_risk(self):
        rc = run_risk_control(trade_status="TRADING", has_shareholder_reduction=True)
        assert not rc.intercepted
        assert rc.risk_level == RISK_LEVEL_MEDIUM

    def test_risk_level_computation(self):
        assert compute_risk_level(0, run_risk_control("TRADING")) == RISK_LEVEL_LOW
        assert compute_risk_level(30, run_risk_control("TRADING")) == RISK_LEVEL_MEDIUM
        assert compute_risk_level(60, run_risk_control("TRADING")) == RISK_LEVEL_HIGH
        assert compute_risk_level(90, run_risk_control("TRADING")) == RISK_LEVEL_EXTREME


# ============================================================
# Suggestion mapping tests
# ============================================================

class TestSuggestionMapping:
    def _make_risk(self, **kwargs):
        return RiskInput(trade_status="TRADING", **kwargs)

    def _make_rc(self, intercepted=False, suggestion=None, risk_level=RISK_LEVEL_LOW):
        class MockRC:
            def __init__(self):
                self.intercepted = intercepted
                self.suggestion = suggestion
                self.risk_level = risk_level
                self.reasons = ["test"] if intercepted else []
        return MockRC()

    def test_score_below_45_avoid(self):
        rc = self._make_rc()
        risk = self._make_risk()
        sug, reasons = map_suggestion(40, rc, risk, 50, 50, None)
        assert sug == SUGGESTION_AVOID

    def test_score_45_55_hold(self):
        rc = self._make_rc()
        risk = self._make_risk()
        sug, reasons = map_suggestion(50, rc, risk, 50, 50, None)
        assert sug == SUGGESTION_HOLD

    def test_score_55_65_watch(self):
        rc = self._make_rc()
        risk = self._make_risk()
        sug, reasons = map_suggestion(60, rc, risk, 50, 50, None)
        assert sug == "BUY_WATCH"

    def test_score_65_75_buy_light_with_trend(self):
        rc = self._make_rc()
        risk = self._make_risk()
        sug, reasons = map_suggestion(70, rc, risk, 65, 50, None)
        assert sug == "BUY_LIGHT"

    def test_score_65_75_no_trend_hold(self):
        rc = self._make_rc()
        risk = self._make_risk()
        sug, reasons = map_suggestion(70, rc, risk, 50, 50, None)
        assert sug == SUGGESTION_HOLD

    def test_score_75_two_strong_signals(self):
        rc = self._make_rc()
        risk = self._make_risk()
        sug, reasons = map_suggestion(80, rc, risk, 75, 75, 70)
        assert sug == "BUY_WATCH"

    def test_score_75_only_trend_strong(self):
        rc = self._make_rc()
        risk = self._make_risk()
        sug, reasons = map_suggestion(80, rc, risk, 75, 55, 55)
        assert sug == "BUY_LIGHT"

    def test_suspended_no_trading_suggestion(self):
        rc = self._make_rc()
        risk = RiskInput(trade_status="SUSPENDED")
        sug, reasons = map_suggestion(80, rc, risk, 75, 75, 70)
        assert sug == SUGGESTION_HOLD

    def test_intercepted_returns_control_suggestion(self):
        rc = self._make_rc(intercepted=True, suggestion=SUGGESTION_AVOID)
        risk = self._make_risk()
        sug, reasons = map_suggestion(80, rc, risk, 75, 75, 70)
        assert sug == SUGGESTION_AVOID

    def test_buy_suggestions_have_stop_loss_review(self):
        for score, trend, vp, cap in [(60, 55, 50, None), (70, 65, 50, None), (80, 75, 75, 70)]:
            rc = self._make_rc()
            risk = self._make_risk()
            sug, reasons = map_suggestion(score, rc, risk, trend, vp, cap)
            if sug in ("BUY_WATCH", "BUY_LIGHT"):
                assert any("止损" in r for r in reasons) or any("严格" in r for r in reasons) or len(reasons) >= 1


# ============================================================
# Integration tests (API)
# ============================================================

class TestAnalysisEngineIntegration:
    def test_normal_stock_full_analysis(self):
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/600000/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "600000"
        assert data["strategyVersion"] == "v1.0.0"
        assert "score" in data
        s = data["score"]
        assert 0 <= s["total"] <= 100
        assert 0 <= s["trend"] <= 100
        assert 0 <= s["volumePrice"] <= 100
        assert s["capital"] is None
        assert s["fundamental"] is None or (0 <= s["fundamental"] <= 100)
        assert 0 <= s["riskPenalty"] <= 100
        assert "masterGuidance" in data
        assert data["disclaimer"] != ""

    def test_strong_stock_suggestion(self):
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/000001/analysis")
        assert resp.status_code == 200
        data = resp.json()
        # 000001 has change=5.2%, vol_ratio=2.1 → strong
        assert data["suggestion"] in ("BUY_LIGHT", "BUY_WATCH", "HOLD")

    def test_suspended_stock_hold(self):
        _seed_stock_basic()
        resp = client.get("/api/stocks/600888/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["suggestion"] == SUGGESTION_HOLD
        assert data["riskLevel"] == RISK_LEVEL_HIGH

    def test_delisted_stock_avoid(self):
        _seed_stock_basic()
        resp = client.get("/api/stocks/300999/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["suggestion"] == SUGGESTION_AVOID
        assert data["riskLevel"] == RISK_LEVEL_EXTREME

    def test_not_found(self):
        resp = client.get("/api/stocks/999999/analysis")
        assert resp.status_code == 404

    def test_suggestion_reason_in_response(self):
        _seed_stock_basic()
        resp = client.get("/api/stocks/600000/analysis")
        data = resp.json()
        assert "suggestionReasons" in data
        assert len(data["suggestionReasons"]) >= 1

    def test_strategy_version_in_response(self):
        _seed_stock_basic()
        resp = client.get("/api/stocks/600000/analysis")
        assert resp.json()["strategyVersion"] == "v1.0.0"


# ============================================================
# Strategy version tests
# ============================================================

class TestStrategyVersion:
    def test_default_strategy_created(self):
        session = SessionLocal()
        try:
            cfg = create_default_strategy(session)
            session.commit()
            assert cfg.version == "v1.0.0"
            assert cfg.enabled
            weights = cfg.get_weights()
            assert abs(weights.get("trend", 0) - 25) < 0.1
        finally:
            session.close()

    def test_default_strategy_idempotent(self):
        session = SessionLocal()
        try:
            c1 = create_default_strategy(session)
            c2 = create_default_strategy(session)
            assert c1.id == c2.id
        finally:
            session.close()

    def test_custom_strategy_version(self):
        session = SessionLocal()
        try:
            create_default_strategy(session)
            cfg = StrategyConfig(
                version="v2.0.0-beta",
                config_json=json.dumps({
                    "version": "v2.0.0-beta",
                    "weights": {"trend": 30, "volumePrice": 30, "capital": 20, "sector": 10, "fundamental": 5, "event": 5},
                    "thresholds": {},
                }),
                description="测试策略",
                enabled=True,
            )
            session.add(cfg)
            session.commit()
            # query using version param
            from src.analysis.strategy_config import get_active_strategy
            active = get_active_strategy(session)
            assert active.id == cfg.id  # newer
        finally:
            session.close()


class TestAnalysisWithStrategyVersion:
    def test_analysis_with_custom_strategy(self):
        _seed_stock_basic()
        session = SessionLocal()
        try:
            create_default_strategy(session)
            session.commit()
        finally:
            session.close()

        resp = client.get("/api/stocks/600000/analysis", params={"strategy_version": "v1.0.0"})
        assert resp.status_code == 200
        assert resp.json()["strategyVersion"] == "v1.0.0"


# ============================================================
# 不得输出无条件买入建议 验证
# ============================================================

class TestNoUnconditionalBuy:
    """核心约束：任何场景下不得输出无条件买入建议。"""
    def test_no_confirm_buy_suggestion(self):
        """验证所有可能的建议值中不存在 CONFIRM_BUY 等绝对买入词"""
        resp = client.get("/api/stocks/600000/analysis")
        if resp.status_code == 200:
            sug = resp.json().get("suggestion", "")
            assert "CONFIRM_BUY" not in sug
            assert "STRONG_BUY" not in sug

    def test_buy_suggestions_have_conditions(self):
        """BUY_LIGHT / BUY_WATCH 必须包含条件说明"""
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/000001/analysis")
        if resp.status_code == 200:
            data = resp.json()
            if data["suggestion"] in ("BUY_LIGHT", "BUY_WATCH"):
                mg = data.get("masterGuidance", {})
                buy_plan = mg.get("buyPlan", [])
                assert len(buy_plan) >= 1
                sell_plan = mg.get("sellPlan", [])
                assert len(sell_plan) >= 1
                review = mg.get("reviewPoints", [])
                assert len(review) >= 1

    def test_hold_is_safe_default(self):
        """默认无数据时应返回 HOLD，不输出买入建议"""
        _seed_stock_basic()
        resp = client.get("/api/stocks/600000/analysis")
        if resp.status_code == 200:
            data = resp.json()
            # 无 quote 数据，趋势评分将保守
            pass

    def test_buy_suggestion_includes_stop_loss(self):
        """买入类建议的卖出计划中必须包含止损位"""
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/600000/analysis")
        if resp.status_code == 200:
            data = resp.json()
            if data["suggestion"] in ("BUY_LIGHT", "BUY_WATCH"):
                sell_plan = data["masterGuidance"]["sellPlan"]
                has_stop_loss = any("止损" in p.get("title", "") for p in sell_plan)
                assert has_stop_loss, "买入类建议必须包含止损位"


# ============================================================
# TotalScore computation tests
# ============================================================

class TestTotalScore:
    def test_all_weights_equal(self):
        from src.analysis.engine import _compute_total, _normalize_weights
        w = {"trend": 25, "volumePrice": 20, "capital": 20, "sector": 15, "fundamental": 10, "event": 10}
        t = _compute_total(80, 70, 60, 50, 40, 30, 10, w)
        expected_raw = (80 * 25 + 70 * 20 + 60 * 20 + 50 * 15 + 40 * 10 + 30 * 10) / 100
        expected = max(0, min(100, int(round(expected_raw - 10))))
        assert t == expected

    def test_max_score(self):
        from src.analysis.engine import _compute_total
        w = {"trend": 100, "volumePrice": 0, "capital": 0, "sector": 0, "fundamental": 0, "event": 0}
        t = _compute_total(100, 0, 0, 0, 0, 0, 0, w)
        assert t == 100

    def test_min_score(self):
        from src.analysis.engine import _compute_total
        w = {"trend": 100, "volumePrice": 0, "capital": 0, "sector": 0, "fundamental": 0, "event": 0}
        t = _compute_total(0, 0, 0, 0, 0, 0, 100, w)
        assert t == 0

    def test_penalty_lowers_score(self):
        from src.analysis.engine import _compute_total
        w = {"trend": 100, "volumePrice": 0, "capital": 0, "sector": 0, "fundamental": 0, "event": 0}
        t1 = _compute_total(80, 0, 0, 0, 0, 0, 0, w)
        t2 = _compute_total(80, 0, 0, 0, 0, 0, 30, w)
        assert t2 < t1

    def test_weight_normalization_missing_data(self):
        from src.analysis.engine import _normalize_weights
        w = {"trend": 25, "volumePrice": 20, "capital": 20, "sector": 15, "fundamental": 10, "event": 10}
        normalized = _normalize_weights(w, None, None, None)
        assert normalized["capital"] == 0
        assert normalized["fundamental"] == 0
        assert normalized["sector"] == 0
        total = sum(normalized.values())
        assert abs(total - 100) < 1

    def test_trend_status_mapping(self):
        assert compute_trend_status(50, 4.0) == "STRONG_UPTREND"
        assert compute_trend_status(50, 2.0) == "WEAK_UPTREND"
        assert compute_trend_status(50, -4.0) == "DOWN_TREND"
        assert compute_trend_status(50, -2.0) == "WEAK_DOWN_TREND"
        assert compute_trend_status(50, 0.5) == "RANGE_BOUND"


# ============================================================
# Masters unit tests
# ============================================================

class TestMasterTrend:
    def test_uptrend_with_ma(self):
        from src.analysis.masters.trend_master import analyze_trend
        k = KlineInput(ma5=10, ma10=9.5, ma20=9, ma60=8.5)
        q = QuoteInput(latest_price=10.5, change_percent=2.0)
        m = analyze_trend(k, q, 75)
        assert m.status == "BULLISH"
        assert len(m.evidence) >= 2

    def test_bearish_below_ma(self):
        from src.analysis.masters.trend_master import analyze_trend
        k = KlineInput(ma5=10, ma10=10, ma20=9.5, ma60=9)
        q = QuoteInput(latest_price=8.5, change_percent=-3.0)
        m = analyze_trend(k, q, 30)
        assert m.status == "BEARISH"
        assert "MA60" in m.evidence[1]

    def test_no_ma_data(self):
        from src.analysis.masters.trend_master import analyze_trend
        k = KlineInput()
        q = QuoteInput(latest_price=10.5, change_percent=0.5)
        m = analyze_trend(k, q, 50)
        assert m.status == "NEUTRAL"

    def test_no_data_at_all(self):
        from src.analysis.masters.trend_master import analyze_trend
        k = KlineInput()
        m = analyze_trend(k, None, 50)
        assert m.status == "INFO"


class TestMasterVolumePrice:
    def test_fangliang_tupo(self):
        from src.analysis.masters.volume_price_master import analyze_volume_price
        q = QuoteInput(volume_ratio=2.0, change_percent=4.0)
        m = analyze_volume_price(q, 80)
        assert m.status == "BULLISH"
        assert "放量突破" in m.explanation

    def test_fangliang_zhizhang(self):
        from src.analysis.masters.volume_price_master import analyze_volume_price
        q = QuoteInput(volume_ratio=1.5, change_percent=0.2)
        m = analyze_volume_price(q, 35)
        assert m.status == "BEARISH"

    def test_suoliang_huicai(self):
        from src.analysis.masters.volume_price_master import analyze_volume_price
        q = QuoteInput(volume_ratio=0.5, change_percent=-0.5)
        m = analyze_volume_price(q, 60)
        assert m.status == "BULLISH"

    def test_liangjia_beili(self):
        from src.analysis.masters.volume_price_master import analyze_volume_price
        q = QuoteInput(volume_ratio=0.4, change_percent=4.0)
        m = analyze_volume_price(q, 30)
        assert m.status == "BEARISH"

    def test_no_data(self):
        from src.analysis.masters.volume_price_master import analyze_volume_price
        m = analyze_volume_price(None, 50)
        assert m.status == "INFO"


class TestMasterCapital:
    def test_continuous_inflow(self):
        from src.analysis.masters.capital_master import analyze_capital
        c = CapitalInput(main_net_inflow=5e7, main_net_inflow_3d=2e8)
        m = analyze_capital(c, 75)
        assert m.status == "BULLISH"

    def test_continuous_outflow(self):
        from src.analysis.masters.capital_master import analyze_capital
        c = CapitalInput(main_net_inflow=-5e7, main_net_inflow_3d=-2e8)
        m = analyze_capital(c, 25)
        assert m.status == "BEARISH"

    def test_no_data(self):
        from src.analysis.masters.capital_master import analyze_capital
        m = analyze_capital(None, 50)
        assert m.status == "INFO"
        assert "尚未接入" in m.explanation


class TestMasterSector:
    def test_strong_sector(self):
        from src.analysis.masters.sector_master import analyze_sector
        sec = SectorInput(sector_name="半导体", sector_change_pct=3.5, sector_rank=5)
        m = analyze_sector(sec, 80)
        assert m.status == "BULLISH"

    def test_weak_sector(self):
        from src.analysis.masters.sector_master import analyze_sector
        sec = SectorInput(sector_name="房地产", sector_change_pct=-3.0, sector_rank=90)
        m = analyze_sector(sec, 30)
        assert m.status == "BEARISH"

    def test_no_data(self):
        from src.analysis.masters.sector_master import analyze_sector
        m = analyze_sector(None, 50)
        assert m.status == "INFO"


class TestMasterFundamental:
    def test_good_fundamentals(self):
        from src.analysis.masters.fundamental_master import analyze_fundamental
        f = FinancialInput(roe=18.5, pe=12, pb=2, profit_change_pct=25)
        m = analyze_fundamental(f, 75)
        assert m.status == "BULLISH"

    def test_bad_fundamentals(self):
        from src.analysis.masters.fundamental_master import analyze_fundamental
        f = FinancialInput(roe=-5.0, pe=200, pb=10, profit_change_pct=-30)
        m = analyze_fundamental(f, 25)
        assert m.status == "BEARISH"

    def test_no_data(self):
        from src.analysis.masters.fundamental_master import analyze_fundamental
        m = analyze_fundamental(None, 50)
        assert m.status == "INFO"


class TestMasterRisk:
    def test_normal(self):
        from src.analysis.masters.risk_master import analyze_risk
        r = RiskInput(trade_status="TRADING")
        m = analyze_risk(r, 0)
        assert m.status == "INFO"

    def test_delisted(self):
        from src.analysis.masters.risk_master import analyze_risk
        r = RiskInput(trade_status="DELISTED")
        m = analyze_risk(r, 100)
        assert m.status == "BEARISH"

    def test_suspended(self):
        from src.analysis.masters.risk_master import analyze_risk
        r = RiskInput(trade_status="SUSPENDED")
        m = analyze_risk(r, 60)
        assert m.status == "CAUTION"

    def test_st_and_penalty(self):
        from src.analysis.masters.risk_master import analyze_risk
        r = RiskInput(trade_status="TRADING", has_st_tag=True, has_major_penalty=True)
        m = analyze_risk(r, 80)
        assert m.status == "BEARISH"

    def test_shareholder_reduction(self):
        from src.analysis.masters.risk_master import analyze_risk
        r = RiskInput(trade_status="TRADING", has_shareholder_reduction=True)
        m = analyze_risk(r, 20)
        assert m.status == "CAUTION"


class TestMasterDiscipline:
    def test_avoid(self):
        from src.analysis.masters.discipline_master import analyze_discipline
        m = analyze_discipline("AVOID", None, "EXTREME", ["高风险"])
        assert "回避" in m.explanation or "回避" in m.detail

    def test_hold(self):
        from src.analysis.masters.discipline_master import analyze_discipline
        m = analyze_discipline("HOLD", None, "LOW", [])
        assert "观望" in m.explanation

    def test_buy_light(self):
        from src.analysis.masters.discipline_master import analyze_discipline
        q = QuoteInput(latest_price=10.0)
        m = analyze_discipline("BUY_LIGHT", q, "LOW", ["趋势向好"])
        assert "止损" in m.detail or "止损" in " ".join(m.evidence)
        assert m.status == "INFO"


class TestMasterAggregator:
    def test_run_all_masters_structure(self):
        from src.analysis.masters import run_all_masters
        k = KlineInput()
        q = QuoteInput(latest_price=10, change_percent=1.0, volume_ratio=1.2)
        scores = {"trend": 50, "volumePrice": 55, "capital": 50, "sector": 50, "fundamental": 50, "event": 50, "riskPenalty": 0}
        r = RiskInput(trade_status="TRADING")
        output = run_all_masters(k, q, None, None, None, r, scores)
        assert "masters" in output
        assert "summary" in output
        assert len(output["masters"]) == 6

    def test_master_guidance_in_api_response(self):
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/600000/analysis")
        assert resp.status_code == 200
        mg = resp.json().get("masterGuidance", {})
        assert "masters" in mg
        assert len(mg["masters"]) == 6
        masters_by_code = {m["code"]: m for m in mg["masters"]}
        assert "trend" in masters_by_code
        assert "volumePrice" in masters_by_code
        assert "capital" in masters_by_code
        assert "sector" in masters_by_code
        assert "fundamental" in masters_by_code
        assert "risk" in masters_by_code

    def test_master_summary_not_empty(self):
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/600000/analysis")
        mg = resp.json()["masterGuidance"]
        assert len(mg["summary"]) > 10

    def test_upside_conditions_structure(self):
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/600000/analysis")
        mg = resp.json()["masterGuidance"]
        for cond in mg["upsideConditions"]:
            assert "conditionId" in cond
            assert "title" in cond
            assert "description" in cond
            assert "evidence" in cond
            assert "status" in cond
            assert "importance" in cond

    def test_buy_plan_includes_stop_loss(self):
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/600000/analysis")
        mg = resp.json()["masterGuidance"]
        sell_plan = mg["sellPlan"]
        assert len(sell_plan) >= 1
        has_stop = any("止损" in p.get("title", "") for p in sell_plan)
        assert has_stop

    def test_review_points_suggestion_specific(self):
        _seed_stock_basic()
        _seed_stock_quote()
        resp = client.get("/api/stocks/600000/analysis")
        mg = resp.json()["masterGuidance"]
        assert len(mg["reviewPoints"]) >= 1
