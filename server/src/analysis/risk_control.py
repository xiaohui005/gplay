TREND_STATUS_STRONG_UPTREND = "STRONG_UPTREND"
TREND_STATUS_WEAK_UPTREND = "WEAK_UPTREND"
TREND_STATUS_RANGE_BOUND = "RANGE_BOUND"
TREND_STATUS_WEAK_DOWN_TREND = "WEAK_DOWN_TREND"
TREND_STATUS_DOWN_TREND = "DOWN_TREND"

RISK_LEVEL_LOW = "LOW"
RISK_LEVEL_MEDIUM = "MEDIUM"
RISK_LEVEL_HIGH = "HIGH"
RISK_LEVEL_EXTREME = "EXTREME"

SUGGESTION_BUY_WATCH = "BUY_WATCH"
SUGGESTION_BUY_LIGHT = "BUY_LIGHT"
SUGGESTION_HOLD = "HOLD"
SUGGESTION_REDUCE = "REDUCE"
SUGGESTION_SELL = "SELL"
SUGGESTION_AVOID = "AVOID"


class RiskControlResult:
    def __init__(self):
        self.intercepted: bool = False
        self.suggestion: str | None = None
        self.risk_level: str = RISK_LEVEL_LOW
        self.penalty: int = 0
        self.reasons: list[str] = []


def run_risk_control(
    trade_status: str,
    has_st_tag: bool = False,
    has_delist_risk: bool = False,
    has_major_penalty: bool = False,
    has_shareholder_reduction: bool = False,
    has_pledge_risk: bool = False,
    delay_minutes: int = 0,
    data_missing: bool = False,
) -> RiskControlResult:
    result = RiskControlResult()
    critical = False

    if trade_status == "DELISTED":
        result.intercepted = True
        result.suggestion = SUGGESTION_AVOID
        result.risk_level = RISK_LEVEL_EXTREME
        result.reasons.append("股票已退市")
        return result

    if trade_status == "SUSPENDED":
        result.intercepted = True
        result.suggestion = SUGGESTION_HOLD
        result.risk_level = RISK_LEVEL_HIGH
        result.reasons.append("股票停牌中，不生成交易建议")
        return result

    if has_st_tag:
        result.intercepted = True
        result.suggestion = SUGGESTION_AVOID
        result.risk_level = RISK_LEVEL_EXTREME
        result.reasons.append("ST/ST* 风险警示")
        critical = True

    if has_delist_risk:
        result.intercepted = True
        result.suggestion = SUGGESTION_AVOID
        result.risk_level = RISK_LEVEL_EXTREME
        result.reasons.append("退市风险警示")
        critical = True

    if has_major_penalty:
        result.intercepted = True
        result.suggestion = SUGGESTION_AVOID
        result.risk_level = RISK_LEVEL_EXTREME
        result.reasons.append("重大监管处罚")
        critical = True

    if data_missing:
        if not critical:
            result.intercepted = True
            result.suggestion = SUGGESTION_HOLD
            result.risk_level = RISK_LEVEL_HIGH
            result.reasons.append("关键数据缺失，暂不生成交易建议")

    if has_shareholder_reduction:
        result.reasons.append("存在股东减持")
        if not critical:
            result.risk_level = max_level(result.risk_level, RISK_LEVEL_MEDIUM)

    if has_pledge_risk:
        result.reasons.append("存在质押风险")
        if not critical:
            result.risk_level = max_level(result.risk_level, RISK_LEVEL_MEDIUM)

    if delay_minutes > 120:
        result.reasons.append(f"数据延迟 {delay_minutes} 分钟，超过阈值")
        if not critical:
            result.intercepted = True
            result.suggestion = SUGGESTION_HOLD
            result.risk_level = max_level(result.risk_level, RISK_LEVEL_HIGH)

    return result


def compute_risk_level(
    penalty: int,
    risk_control: RiskControlResult,
) -> str:
    if risk_control.risk_level in (RISK_LEVEL_EXTREME, RISK_LEVEL_HIGH):
        return risk_control.risk_level
    if penalty >= 80:
        return RISK_LEVEL_EXTREME
    if penalty >= 50:
        return RISK_LEVEL_HIGH
    if penalty >= 20:
        return RISK_LEVEL_MEDIUM
    return RISK_LEVEL_LOW


def compute_trend_status(
    trend_score: int,
    change_percent: float | None = None,
) -> str:
    if change_percent is not None:
        if change_percent >= 3:
            return TREND_STATUS_STRONG_UPTREND
        if change_percent >= 1:
            return TREND_STATUS_WEAK_UPTREND
        if change_percent <= -3:
            return TREND_STATUS_DOWN_TREND
        if change_percent <= -1:
            return TREND_STATUS_WEAK_DOWN_TREND
    if trend_score >= 70:
        return TREND_STATUS_WEAK_UPTREND
    if trend_score >= 60:
        return TREND_STATUS_RANGE_BOUND
    if trend_score <= 35:
        return TREND_STATUS_DOWN_TREND
    return TREND_STATUS_RANGE_BOUND


def max_level(a: str, b: str) -> str:
    order = [RISK_LEVEL_LOW, RISK_LEVEL_MEDIUM, RISK_LEVEL_HIGH, RISK_LEVEL_EXTREME]
    return order[max(order.index(a), order.index(b))]
