from src.analysis.datatypes import RiskInput, StrategyWeights
from src.analysis.risk_control import (
    RISK_LEVEL_EXTREME,
    RISK_LEVEL_HIGH,
    SUGGESTION_AVOID,
    SUGGESTION_BUY_LIGHT,
    SUGGESTION_BUY_WATCH,
    SUGGESTION_HOLD,
    SUGGESTION_REDUCE,
    SUGGESTION_SELL,
    RiskControlResult,
)


def map_suggestion(
    total_score: int,
    risk_control: RiskControlResult,
    risk: RiskInput,
    trend_score: int,
    volume_price_score: int,
    capital_score: int | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if risk_control.intercepted:
        msg = risk_control.suggestion or SUGGESTION_HOLD
        return msg, risk_control.reasons

    if risk.trade_status != "TRADING":
        return SUGGESTION_HOLD, ["当前股票非交易状态，不生成交易建议"]

    if risk.data_missing:
        return SUGGESTION_HOLD, ["数据不足，暂时观望"]

    if total_score < 45:
        return SUGGESTION_AVOID, [f"综合评分 {total_score}，低于风险阈值，建议回避"]

    if 45 <= total_score < 55:
        return SUGGESTION_HOLD, [f"综合评分 {total_score}，处于观望区间"]

    if total_score >= 75:
        strong_count = 0
        if trend_score >= 70:
            strong_count += 1
        if volume_price_score >= 70:
            strong_count += 1
        if capital_score is not None and capital_score >= 70:
            strong_count += 1

        if strong_count >= 2:
            return SUGGESTION_BUY_WATCH, [
                f"综合评分 {total_score}，趋势/量价/资金至少两项偏强",
                "回踩关键支撑不破可关注",
            ]
        if trend_score >= 70:
            return SUGGESTION_BUY_LIGHT, [
                f"综合评分 {total_score}，趋势偏强",
                "轻仓试探，严格设置止损",
            ]
        return SUGGESTION_HOLD, [f"综合评分 {total_score}，分数较高但缺乏核心信号确认"]

    if 65 <= total_score < 75:
        if trend_score >= 60:
            return SUGGESTION_BUY_LIGHT, [
                f"综合评分 {total_score}，趋势转强且风险不高",
                "轻仓试探，严格设置止损位",
            ]
        return SUGGESTION_HOLD, [
            f"综合评分 {total_score}，趋势尚未确认，继续观望",
        ]

    if 55 <= total_score < 65:
        return SUGGESTION_BUY_WATCH, [
            f"综合评分 {total_score}，趋势或资金有改善但未确认",
            "放入关注列表，等待更强信号",
        ]

    return SUGGESTION_HOLD, ["暂不满足操作条件"]


def check_sell_conditions(
    total_score: int,
    prev_total_score: int | None,
    risk_control: RiskControlResult,
) -> tuple[str | None, list[str]]:
    reasons: list[str] = []

    if risk_control.intercepted and risk_control.suggestion in (
        SUGGESTION_AVOID,
        SUGGESTION_HOLD,
    ):
        if risk_control.suggestion == SUGGESTION_AVOID:
            return SUGGESTION_SELL, ["风控拦截：高风险触发卖出条件"]

    if total_score < 45:
        return SUGGESTION_SELL, [f"综合评分 {total_score} 跌破 45，触发卖出条件"]

    if prev_total_score is not None:
        drop = prev_total_score - total_score
        if drop >= 20:
            return SUGGESTION_REDUCE, [
                f"综合评分从 {prev_total_score} 降至 {total_score}，降幅 {drop} 分",
                "建议减仓观察",
            ]

    return None, []
