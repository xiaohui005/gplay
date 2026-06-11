import json
from datetime import datetime, timezone

from src.analysis.datatypes import (
    DISCLAIMER,
    CapitalInput,
    EventInput,
    FinancialInput,
    KlineInput,
    QuoteInput,
    RiskInput,
    SectorInput,
)
from src.analysis.masters import run_all_masters, run_discipline_masters
from src.analysis.risk_control import (
    compute_risk_level,
    compute_trend_status,
    run_risk_control,
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
from src.analysis.strategy_config import (
    AnalysisResult,
    StrategyConfig,
    get_active_strategy,
)
from src.analysis.suggestion import check_sell_conditions, map_suggestion
from src.repositories.stock_basic_repo import StockBasicRepo
from src.repositories.stock_quote_snapshot_repo import StockQuoteSnapshotRepo


class AnalysisEngine:
    def __init__(self, db_session):
        self.db = db_session
        self.basic_repo = StockBasicRepo(db_session)
        self.quote_repo = StockQuoteSnapshotRepo(db_session)

    def analyze(self, symbol: str, strategy_version: str | None = None) -> dict | None:
        basic = self.basic_repo.get_by_symbol(symbol)
        if basic is None:
            return None

        quote = self.quote_repo.get_latest_by_symbol(symbol)

        quote_input = _build_quote_input(quote)
        kline_input = KlineInput()
        capital_input = None
        financial_input = None
        sector_input = None
        event_input = None

        risk_input = RiskInput(
            trade_status=basic.trade_status,
            delay_minutes=quote.delay_minutes if quote else 0,
            data_missing=quote is None,
        )

        risk_control = run_risk_control(
            trade_status=risk_input.trade_status,
            has_st_tag=risk_input.has_st_tag,
            has_delist_risk=risk_input.has_delist_risk,
            has_major_penalty=risk_input.has_major_penalty,
            has_shareholder_reduction=risk_input.has_shareholder_reduction,
            has_pledge_risk=risk_input.has_pledge_risk,
            delay_minutes=risk_input.delay_minutes,
            data_missing=risk_input.data_missing,
        )

        strategy = _resolve_strategy(self.db, strategy_version)
        weights = strategy.get_weights()

        trend_score = score_trend(kline_input, quote_input)
        vp_score = score_volume_price(quote_input)
        cap_score = score_capital(capital_input)
        sec_score = score_sector(sector_input)
        fund_score = score_fundamental(financial_input)
        evt_score = score_event(event_input)
        risk_penalty = compute_risk_penalty(risk_input)

        effective_weights = _normalize_weights(weights, capital_input, financial_input, sector_input)

        total_score = _compute_total(
            trend_score,
            vp_score,
            cap_score,
            sec_score,
            fund_score,
            evt_score,
            risk_penalty,
            effective_weights,
        )

        risk_level = compute_risk_level(risk_penalty, risk_control)
        trend_status = compute_trend_status(trend_score, quote_input.change_percent)
        suggestion, sug_reasons = map_suggestion(
            total_score,
            risk_control,
            risk_input,
            trend_score,
            vp_score,
            cap_score,
        )

        data_time = (quote_input.data_time or datetime.now(timezone.utc)).isoformat()

        scores = {
            "total": total_score,
            "trend": trend_score,
            "volumePrice": vp_score,
            "capital": cap_score,
            "sector": sec_score,
            "fundamental": fund_score,
            "event": evt_score,
            "riskPenalty": risk_penalty,
        }

        master_output = run_all_masters(
            kline_input, quote_input, capital_input, sector_input, financial_input, risk_input, scores
        )

        discipline_output = run_discipline_masters(
            suggestion, quote_input, risk_level, sug_reasons, master_output["masters_raw"]
        )

        result = {
            "symbol": basic.symbol,
            "market": basic.market,
            "dataTime": data_time,
            "delayMinutes": risk_input.delay_minutes,
            "trendStatus": trend_status,
            "riskLevel": risk_level,
            "suggestion": suggestion,
            "suggestionReasons": sug_reasons,
            "strategyVersion": strategy.version,
            "score": {
                "total": total_score,
                "trend": trend_score,
                "volumePrice": vp_score,
                "capital": cap_score if capital_input else None,
                "sector": sec_score,
                "fundamental": fund_score if financial_input else None,
                "event": evt_score if event_input else None,
                "riskPenalty": risk_penalty,
            },
            "masterGuidance": {
                "summary": master_output["summary"],
                "masters": master_output["masters"],
                "upsideConditions": discipline_output["upsideConditions"],
                "pullbackConditions": discipline_output["pullbackConditions"],
                "buyPlan": discipline_output["buyPlan"],
                "sellPlan": discipline_output["sellPlan"],
                "reviewPoints": discipline_output["reviewPoints"],
            },
            "disclaimer": DISCLAIMER,
        }

        self._persist_result(basic.symbol, strategy.version, total_score, suggestion, risk_level, result)

        return result

    def _persist_result(
        self,
        symbol: str,
        strategy_version: str,
        total_score: int,
        suggestion: str,
        risk_level: str,
        result: dict,
    ):
        record = AnalysisResult(
            symbol=symbol,
            strategy_version=strategy_version,
            total_score=total_score,
            suggestion=suggestion,
            risk_level=risk_level,
            result_json=json.dumps(result, ensure_ascii=False),
        )
        self.db.add(record)
        self.db.flush()


def _build_quote_input(quote):
    if quote is None:
        return QuoteInput()
    return QuoteInput(
        latest_price=quote.latest_price,
        change_percent=quote.change_percent,
        volume=quote.volume,
        amount=quote.amount,
        turnover_rate=quote.turnover_rate,
        volume_ratio=quote.volume_ratio,
        high=quote.high,
        low=quote.low,
        open_price=quote.open_price,
        pre_close=quote.pre_close,
        amplitude=quote.amplitude,
        data_time=quote.data_time,
        delay_minutes=quote.delay_minutes or 0,
    )


def _resolve_strategy(db_session, strategy_version: str | None):
    if strategy_version:
        cfg = (
            db_session.query(StrategyConfig)
            .filter(StrategyConfig.version == strategy_version)
            .first()
        )
        if cfg:
            return cfg
    return get_active_strategy(db_session)


def _normalize_weights(weights: dict, capital_input, financial_input, sector_input):
    raw = {
        "trend": float(weights.get("trend", 25)),
        "volumePrice": float(weights.get("volumePrice", 20)),
        "capital": float(weights.get("capital", 20)),
        "sector": float(weights.get("sector", 15)),
        "fundamental": float(weights.get("fundamental", 10)),
        "event": float(weights.get("event", 10)),
    }

    missing = []
    if capital_input is None:
        missing.append("capital")
    if financial_input is None:
        missing.append("fundamental")
    if sector_input is None:
        missing.append("sector")

    if not missing:
        return raw

    removed_sum = sum(raw[k] for k in missing)
    remaining_count = len([k for k in raw.keys() if k not in missing])

    if remaining_count == 0:
        return {"trend": 100.0}

    redistribution = removed_sum / remaining_count

    for k in missing:
        raw[k] = 0.0

    for k in raw:
        if raw[k] > 0:
            raw[k] += redistribution

    total = sum(raw.values())
    if abs(total - 100.0) > 0.01:
        factor = 100.0 / total
        for k in raw:
            raw[k] *= factor

    return raw


def _compute_total(
    trend: int,
    vp: int,
    capital: int,
    sector: int,
    fundamental: int,
    event: int,
    penalty: int,
    weights: dict,
) -> int:
    raw = (
        trend * weights.get("trend", 0) / 100.0
        + vp * weights.get("volumePrice", 0) / 100.0
        + capital * weights.get("capital", 0) / 100.0
        + sector * weights.get("sector", 0) / 100.0
        + fundamental * weights.get("fundamental", 0) / 100.0
        + event * weights.get("event", 0) / 100.0
    )
    result = raw - penalty
    return max(0, min(100, int(round(result))))


def _build_summary_text(name: str, trend: str, risk: str, score: int, suggestion: str) -> str:
    trend_map = {
        "STRONG_UPTREND": "强势上涨",
        "WEAK_UPTREND": "震荡偏强",
        "RANGE_BOUND": "震荡整理",
        "WEAK_DOWN_TREND": "震荡偏弱",
        "DOWN_TREND": "弱势下跌",
    }
    risk_map = {"LOW": "低风险", "MEDIUM": "中风险", "HIGH": "高风险", "EXTREME": "极高风险"}
    sug_map = {
        "BUY_WATCH": "关注",
        "BUY_LIGHT": "轻仓试探",
        "HOLD": "持有观望",
        "REDUCE": "减仓",
        "SELL": "卖出",
        "AVOID": "回避",
    }
    return f"{name}当前处于{trend_map.get(trend, '未知')}状态，{risk_map.get(risk, '未知风险等级')}，综合评分{score}分，建议{sug_map.get(suggestion, '观望')}。"


def _build_master_guidance(
    name: str,
    trend: str,
    risk: str,
    score: int,
    quote: QuoteInput,
    suggestion: str,
    reasons: list[str],
) -> dict:
    summary = _build_summary_text(name, trend, risk, score, suggestion)

    upside = _build_upside_conditions(trend, quote)
    pullback = _build_pullback_conditions(trend, quote)
    buy_plan = _build_buy_plan(suggestion, quote, reason_hint=reasons[0] if reasons else "")
    sell_plan = _build_sell_plan(suggestion, risk, quote)
    review = _build_review_points(suggestion, reasons, quote)

    return {
        "summary": summary,
        "upsideConditions": upside,
        "pullbackConditions": pullback,
        "buyPlan": buy_plan,
        "sellPlan": sell_plan,
        "reviewPoints": review,
    }


def _build_upside_conditions(trend: str, quote: QuoteInput) -> list[dict]:
    if quote.latest_price is None:
        return [_cond("UP-1", "等待首笔行情", "获取实时数据后判断", "行情数据", "NOT_MET", "MEDIUM")]
    p = quote.latest_price
    items = [
        _cond("UP-1", f"放量突破 {p * 1.03:.2f}", "成交量放大突破3%阻力位确认", "价格突破", "NOT_MET", "HIGH"),
    ]
    if quote.volume_ratio is not None:
        items.append(_cond("UP-2", f"量比 > 1.5（当前 {quote.volume_ratio:.2f}）", "成交量确认突破有效性", "量比", "NOT_MET", "HIGH"))
    else:
        items.append(_cond("UP-2", "量比 > 1.5", "成交量确认突破有效性", "量比", "NOT_MET", "HIGH"))
    items.append(_cond("UP-3", "均线多头排列", "短期均线上穿中长期均线", "均线系统", "NOT_MET", "MEDIUM"))
    return items


def _build_pullback_conditions(trend: str, quote: QuoteInput) -> list[dict]:
    if quote.latest_price is None:
        return [_cond("DOWN-1", "等待首笔行情", "获取实时数据后判断", "行情数据", "NOT_MET", "MEDIUM")]
    p = quote.latest_price
    items = [
        _cond("DOWN-1", f"跌破 {p * 0.97:.2f}", "3%回撤触发回调预警", "价格回撤", "NOT_MET", "HIGH"),
        _cond("DOWN-2", f"量比 < 0.5（当前 {quote.volume_ratio:.2f}）", "缩量下跌抛压减弱", "量比", "NOT_MET", "MEDIUM")
        if quote.volume_ratio is not None
        else _cond("DOWN-2", "量比 < 0.5", "缩量下跌抛压减弱", "量比", "NOT_MET", "MEDIUM"),
    ]
    return items


def _build_buy_plan(suggestion: str, quote: QuoteInput, reason_hint: str = "") -> list[dict]:
    if suggestion == "AVOID":
        return [_plan("操作建议", "当前风险过高，建议回避", "不适用", 0)]

    if suggestion in ("HOLD",):
        if quote.latest_price is None:
            return [_plan("操作建议", "等待明确信号", "数据不足", 0)]
        return [
            _plan("关注位", f"{quote.latest_price * 0.95:.2f}", "跌破关键支撑观察", 0),
        ]

    if quote.latest_price is None:
        return [_plan("关注位", "-", "等待行情数据", 0)]

    p = quote.latest_price
    if suggestion == "BUY_LIGHT":
        return [
            _plan("止损位", f"{p * 0.93:.2f}", "跌破7%无条件止损", 100),
            _plan("试探位", f"{p * 1.02:.2f}", "放量突破2%轻仓试探", 30),
            _plan("确认位", f"{p * 1.05:.2f}", "站稳5%可适当加仓", 50),
        ]

    if suggestion == "BUY_WATCH":
        return [
            _plan("关注位", f"{p * 0.95:.2f}", "回踩5%不破可关注", 20),
            _plan("试探位", f"{p * 1.02:.2f}", "放量突破2%考虑试探", 30),
        ]

    return [
        _plan("关注位", f"{p * 0.95:.2f}", "跌破关键支撑观察", 0),
    ]


def _build_sell_plan(suggestion: str, risk: str, quote: QuoteInput) -> list[dict]:
    if risk in ("EXTREME", "HIGH") or suggestion == "AVOID":
        return [
            _plan("止损位", "当前价", "风险过高，建议离场", 100),
        ]

    if suggestion == "SELL":
        return [
            _plan("卖出触发", "已触发卖出条件", "建议执行止损", 100),
        ]

    if suggestion == "REDUCE":
        return [
            _plan("减仓触发", "风险升高或趋势转弱", "建议减仓至半仓以下", 50),
        ]

    if quote.latest_price is None:
        return [
            _plan("止损位", "-", "等待行情数据", 100),
        ]

    p = quote.latest_price
    return [
        _plan("止损位", f"{p * 0.93:.2f}", "跌破7%严格止损", 100),
        _plan("止盈位", f"{p * 1.10:.2f}", "达到10%目标分批止盈", 50),
    ]


def _build_review_points(suggestion: str, reasons: list[str], quote: QuoteInput) -> list[str]:
    points = []
    if reasons:
        points.append(reasons[0])
    if quote.change_percent is not None:
        points.append(f"当日涨跌幅 {quote.change_percent:+.2f}%")
    if quote.volume_ratio is not None:
        points.append(f"量比 {quote.volume_ratio:.2f}")
    if suggestion in ("BUY_LIGHT", "BUY_WATCH"):
        points.append("所有买入类建议必须设置止损位，严格执行交易纪律")
        points.append("本系统不承诺任何收益，投资决策请自行判断")
    if not points:
        points.append("等待更多数据后更新观察点")
    return points


def _cond(cid: str, title: str, desc: str, evidence: str, status: str, importance: str) -> dict:
    return {
        "conditionId": cid,
        "title": title,
        "description": desc,
        "evidence": [evidence],
        "status": status,
        "importance": importance,
    }


def _plan(title: str, price: str, comment: str, weight: int) -> dict:
    return {"title": title, "price": price, "comment": comment, "weight": weight}
