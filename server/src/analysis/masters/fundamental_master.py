from src.analysis.datatypes import FinancialInput
from src.analysis.masters.base import (
    MASTER_BEARISH,
    MASTER_BULLISH,
    MASTER_INFO,
    MASTER_NEUTRAL,
    MasterConclusion,
)


def analyze_fundamental(financial: FinancialInput | None, score: int) -> MasterConclusion:
    c = MasterConclusion(code="fundamental", name="基本面大师")
    evidence: list[str] = []

    if financial is None:
        c.status = MASTER_INFO
        c.explanation = "财务数据尚未接入，暂时无法进行基本面分析。"
        c.detail = "需要接入财务数据（ROE、PE、PB、净利润增长率等）后才能提供基本面大师分析。"
        evidence.append("数据暂未接入：需授权财务数据")
        evidence.append(f"基本面评分={score}/100（默认中性）")
        c.evidence = evidence
        return c

    if financial.roe is not None:
        evidence.append(f"ROE={financial.roe:.2f}%")
    if financial.pe is not None:
        evidence.append(f"PE={financial.pe:.2f}")
    if financial.pb is not None:
        evidence.append(f"PB={financial.pb:.2f}")
    if financial.profit_change_pct is not None:
        evidence.append(f"净利润增长率={financial.profit_change_pct:+.2f}%")

    positives: list[str] = []
    negatives: list[str] = []

    if financial.roe is not None:
        if financial.roe > 15:
            positives.append(f"ROE {financial.roe:.1f}% > 15%，盈利能力强")
        elif financial.roe > 10:
            positives.append(f"ROE {financial.roe:.1f}%，盈利能力良好")
        elif financial.roe > 5:
            positives.append(f"ROE {financial.roe:.1f}%，盈利能力一般")
        elif financial.roe < 0:
            negatives.append(f"ROE {financial.roe:.1f}%，企业亏损")

    if financial.pe is not None:
        pe = abs(financial.pe)
        if 0 < pe <= 15:
            positives.append(f"PE {financial.pe:.1f}，估值合理偏低")
        elif pe > 50:
            negatives.append(f"PE {financial.pe:.1f}，估值偏高")
        elif pe > 100:
            negatives.append(f"PE {financial.pe:.1f}，估值过高")

    if financial.profit_change_pct is not None:
        if financial.profit_change_pct > 20:
            positives.append(f"净利润增长 {financial.profit_change_pct:+.1f}%，业绩向好")
        elif financial.profit_change_pct > 0:
            positives.append(f"净利润微增 {financial.profit_change_pct:+.1f}%")
        elif financial.profit_change_pct < -20:
            negatives.append(f"净利润下滑 {financial.profit_change_pct:+.1f}%，业绩承压")

    if positives and not negatives:
        c.status = MASTER_BULLISH
        c.explanation = "基本面良好，各项指标健康。"
        c.detail = "；".join(positives) + "。"
    elif positives and negatives:
        c.status = MASTER_NEUTRAL
        c.explanation = "基本面好坏参半，需关注核心矛盾。"
        c.detail = "积极因素：" + "；".join(positives) + "。风险因素：" + "；".join(negatives) + "。"
    elif negatives and not positives:
        c.status = MASTER_BEARISH
        c.explanation = "基本面偏弱，存在多个风险点。"
        c.detail = "；".join(negatives) + "。"
    else:
        c.status = MASTER_INFO
        c.explanation = "基本面数据有限，无法得出明确结论。"
        c.detail = "数据不足以判断基本面状况。"

    evidence.append(f"基本面评分={score}/100")
    c.evidence = evidence
    return c
