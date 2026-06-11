from src.analysis.datatypes import QuoteInput
from src.analysis.masters.base import (
    MASTER_CAUTION,
    MASTER_INFO,
    MASTER_NEUTRAL,
    MasterConclusion,
    cond,
    plan,
)
from src.analysis.risk_control import SUGGESTION_AVOID, SUGGESTION_HOLD


def analyze_discipline(
    suggestion: str,
    quote: QuoteInput | None,
    risk_level: str,
    reasons: list[str],
) -> MasterConclusion:
    c = MasterConclusion(code="discipline", name="交易纪律大师")
    evidence: list[str] = []

    if suggestion == SUGGESTION_AVOID:
        c.status = MASTER_CAUTION
        c.explanation = "当前风险过高，建议严格遵守回避纪律，不进行任何买入操作。"
        c.detail = "风险评级为回避级别，交易纪律要求不操作。耐心等待风险释放。"
        evidence.append("当前建议：回避")
        evidence.append("纪律要求：不买入、不加仓、逐步减仓")
        c.evidence = evidence
        return c

    if suggestion == SUGGESTION_HOLD:
        c.status = MASTER_NEUTRAL
        c.explanation = "持有观望，等待明确信号再行动。"
        c.detail = "当前处于观望区间，交易纪律要求不急于操作。等待以下信号之一出现：放量突破确认、关键支撑验证、风险因素消除。"
        evidence.append("当前建议：持有观望")
        evidence.append("纪律要求：不追高、不杀跌、等待确认")
        c.evidence = evidence
        return c

    if suggestion in ("BUY_LIGHT", "BUY_WATCH"):
        c.status = MASTER_INFO
        c.explanation = "操作前务必确认以下交易纪律。"
        c.detail = "所有买入操作必须设置止损位，严格执行交易计划，不因单次亏损而改变策略。"
        evidence.append("当前建议：" + ("轻仓试探" if suggestion == "BUY_LIGHT" else "关注"))
        evidence.append("纪律一：设置止损位，跌破无条件离场")
        evidence.append("纪律二：分批建仓，不一次性满仓")
        evidence.append("纪律三：买入后持续跟踪失效条件")
        c.evidence = evidence
        return c

    c.status = MASTER_INFO
    c.explanation = "请遵守交易纪律，严格执行止损止盈计划。"
    c.detail = "坚持交易纪律是长期稳定盈利的基础。"
    evidence.append("纪律要求：严格执行计划，不情绪化交易")
    c.evidence = evidence
    return c


def build_buy_plan(suggestion: str, quote: QuoteInput | None, risk_level: str) -> list[dict]:
    if suggestion == SUGGESTION_AVOID:
        return [plan("操作建议", "当前风险过高，建议回避", "不适用", 0)]

    if quote is None or quote.latest_price is None:
        return [plan("关注位", "等待行情数据", "缺少最新行情", 0)]

    p = quote.latest_price

    if suggestion == SUGGESTION_HOLD:
        return [
            plan("关注位", f"{p * 0.95:.2f}", "回踩5%不破可关注", 20),
            plan("确认位", f"{p * 1.03:.2f}", "放量突破3%确认", 50),
        ]

    if suggestion == "BUY_LIGHT":
        return [
            plan("试探位", f"{p * 1.01:.2f}", "突破1%轻仓试探", 20),
            plan("加仓位", f"{p * 1.03:.2f}", "站稳3%可适当加仓", 40),
            plan("满仓位", f"{p * 1.06:.2f}", "趋势确认后逐步加至计划仓位", 60),
        ]

    if suggestion == "BUY_WATCH":
        return [
            plan("关注位", f"{p * 0.95:.2f}", "回踩5%不破可关注", 20),
            plan("试探位", f"{p * 1.02:.2f}", "放量突破2%考虑试探", 30),
        ]

    return [plan("观望", "-", "不满足操作条件", 0)]


def build_sell_plan(suggestion: str, risk_level: str, quote: QuoteInput | None) -> list[dict]:
    if risk_level in ("EXTREME", "HIGH") or suggestion == SUGGESTION_AVOID:
        return [plan("止损位", "当前价", "风险过高，建议离场", 100)]

    if suggestion == "SELL":
        return [plan("卖出触发", "已触发卖出条件", "建议执行止损", 100)]

    if suggestion == "REDUCE":
        return [plan("减仓触发", "风险升高或趋势转弱", "建议减仓至半仓以下", 50)]

    if quote is None or quote.latest_price is None:
        return [plan("止损位", "-", "等待行情数据", 100)]

    p = quote.latest_price

    if suggestion in ("BUY_LIGHT", "BUY_WATCH"):
        return [
            plan("止损位", f"{p * 0.93:.2f}", "跌破7%严格止损", 100),
            plan("止盈位", f"{p * 1.10:.2f}", "达到10%目标分批止盈", 50),
        ]

    return [
        plan("止损位", f"{p * 0.93:.2f}", "跌破7%严格止损", 100),
        plan("止盈位", f"{p * 1.10:.2f}", "达到10%目标分批止盈", 50),
    ]


def build_upside_conditions(suggestion: str, quote: QuoteInput | None, reasons: list[str]) -> list[dict]:
    if quote is None or quote.latest_price is None:
        return [cond("UP-1", "等待首笔行情", "获取实时数据后判断", "行情数据", "NOT_MET", "MEDIUM")]

    p = quote.latest_price
    items = [
        cond("UP-1", f"放量突破 {p * 1.03:.2f}", "成交量放大且价格突破3%阻力位", "价格突破", "NOT_MET", "HIGH"),
    ]
    if quote.volume_ratio is not None:
        items.append(
            cond("UP-2", f"量比 > 1.5（当前 {quote.volume_ratio:.2f}）", "成交量放大确认突破有效性", "量比", "NOT_MET", "HIGH")
        )
    else:
        items.append(cond("UP-2", "量比 > 1.5", "成交量放大确认突破有效性", "量比", "NOT_MET", "HIGH"))

    items.append(cond("UP-3", "均线多头排列", "短期均线上穿中长期均线，MA5 > MA10 > MA20", ["MA5", "MA10", "MA20"], "NOT_MET", "MEDIUM"))
    return items


def build_pullback_conditions(suggestion: str, quote: QuoteInput | None, reasons: list[str]) -> list[dict]:
    if quote is None or quote.latest_price is None:
        return [cond("DOWN-1", "等待首笔行情", "获取实时数据后判断", "行情数据", "NOT_MET", "MEDIUM")]

    p = quote.latest_price
    items = [
        cond("DOWN-1", f"跌破 {p * 0.97:.2f}", "3%回撤触发回调预警", "价格回撤", "NOT_MET", "HIGH"),
    ]
    if quote.volume_ratio is not None:
        items.append(
            cond("DOWN-2", f"量比 < 0.5（当前 {quote.volume_ratio:.2f}）", "缩量下跌抛压减弱", "量比", "NOT_MET", "MEDIUM")
        )
    else:
        items.append(cond("DOWN-2", "量比 < 0.5", "缩量下跌抛压减弱", "量比", "NOT_MET", "MEDIUM"))

    items.append(cond("DOWN-3", "跌破 MA20", "价格跌破20日均线，趋势转弱信号", "MA20", "NOT_MET", "HIGH"))
    return items


def build_review_points(suggestion: str, reasons: list[str], quote: QuoteInput | None, masters: list[MasterConclusion]) -> list[str]:
    points = []
    if reasons:
        points.append(reasons[0])

    for m in masters:
        if m.code in ("trend", "volumePrice", "risk"):
            points.append(m.explanation)

    if quote and quote.change_percent is not None:
        points.append(f"当日涨跌幅 {quote.change_percent:+.2f}%")
    if quote and quote.volume_ratio is not None:
        points.append(f"量比 {quote.volume_ratio:.2f}")

    if suggestion in ("BUY_LIGHT", "BUY_WATCH"):
        points.append("【纪律】买入操作必须设置止损位，严格执行")
        points.append("【风险提示】本系统不承诺任何收益，投资决策请自行判断")

    if suggestion == SUGGESTION_AVOID:
        points.append("【重要】高风险股票，建议回避")

    return points[:8]
