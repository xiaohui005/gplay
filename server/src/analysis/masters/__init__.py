from src.analysis.datatypes import (
    CapitalInput,
    FinancialInput,
    KlineInput,
    QuoteInput,
    RiskInput,
    SectorInput,
)
from src.analysis.masters.base import MasterConclusion
from src.analysis.masters.capital_master import analyze_capital
from src.analysis.masters.discipline_master import (
    build_buy_plan,
    build_pullback_conditions,
    build_review_points,
    build_sell_plan,
    build_upside_conditions,
    analyze_discipline,
)
from src.analysis.masters.fundamental_master import analyze_fundamental
from src.analysis.masters.risk_master import analyze_risk
from src.analysis.masters.sector_master import analyze_sector
from src.analysis.masters.trend_master import analyze_trend
from src.analysis.masters.volume_price_master import analyze_volume_price


def run_all_masters(
    kline: KlineInput,
    quote: QuoteInput | None,
    capital: CapitalInput | None,
    sector: SectorInput | None,
    financial: FinancialInput | None,
    risk: RiskInput,
    scores: dict,
) -> dict:
    trend_m = analyze_trend(kline, quote, scores.get("trend", 50))
    vp_m = analyze_volume_price(quote, scores.get("volumePrice", 50))
    cap_m = analyze_capital(capital, scores.get("capital", 50))
    sec_m = analyze_sector(sector, scores.get("sector", 50))
    fund_m = analyze_fundamental(financial, scores.get("fundamental", 50))
    risk_m = analyze_risk(risk, scores.get("riskPenalty", 0))

    masters = [trend_m, vp_m, cap_m, sec_m, fund_m, risk_m]

    summary = _build_global_summary(masters, scores.get("total", 50))

    return {
        "masters": [_m_to_dict(m) for m in masters],
        "masters_raw": masters,
        "summary": summary,
    }


def run_discipline_masters(
    suggestion: str,
    quote: QuoteInput | None,
    risk_level: str,
    reasons: list[str],
    masters: list[MasterConclusion],
) -> dict:
    disc_m = analyze_discipline(suggestion, quote, risk_level, reasons)

    all_masters = masters + [disc_m]

    return {
        "upsideConditions": build_upside_conditions(suggestion, quote, reasons),
        "pullbackConditions": build_pullback_conditions(suggestion, quote, reasons),
        "buyPlan": build_buy_plan(suggestion, quote, risk_level),
        "sellPlan": build_sell_plan(suggestion, risk_level, quote),
        "reviewPoints": build_review_points(suggestion, reasons, quote, all_masters),
    }


def _build_global_summary(masters: list[MasterConclusion], total_score: int) -> str:
    bullish = sum(1 for m in masters if m.status == "BULLISH")
    bearish = sum(1 for m in masters if m.status == "BEARISH")
    caution = sum(1 for m in masters if m.status == "CAUTION")

    parts = [f"综合评分 {total_score}"]
    if bullish >= 4:
        parts.append("多数大师看多")
    elif bearish >= 4:
        parts.append("多数大师看空")
    elif caution >= 2:
        parts.append("存在风险警示")
    else:
        parts.append("各大师信号分化")

    active = [m for m in masters if m.status not in ("NEUTRAL", "INFO")]
    if active:
        top = active[0]
        parts.append(f"核心关注：{top.explanation}")

    return "。" .join(parts) + "。"


def _m_to_dict(m: MasterConclusion) -> dict:
    return {
        "code": m.code,
        "name": m.name,
        "status": m.status,
        "explanation": m.explanation,
        "detail": m.detail,
        "evidence": m.evidence,
    }
