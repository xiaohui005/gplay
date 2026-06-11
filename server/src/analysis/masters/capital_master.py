from src.analysis.datatypes import CapitalInput
from src.analysis.masters.base import (
    MASTER_BEARISH,
    MASTER_BULLISH,
    MASTER_INFO,
    MASTER_NEUTRAL,
    MasterConclusion,
)


def analyze_capital(capital: CapitalInput | None, score: int) -> MasterConclusion:
    c = MasterConclusion(code="capital", name="资金大师")
    evidence: list[str] = []

    if capital is None:
        c.status = MASTER_INFO
        c.explanation = "资金数据尚未接入，暂时无法分析资金动向。"
        c.detail = "需要接入主力资金流数据（如 Level-2 资金流、北向资金）后才能提供资金大师分析。"
        evidence.append("数据暂未接入：需授权数据源")
        evidence.append(f"资金评分={score}/100（默认中性）")
        c.evidence = evidence
        return c

    evidence.append(f"主力净流入={capital.main_net_inflow:+.2e}" if capital.main_net_inflow is not None else "主力净流入=暂无")
    if capital.main_net_inflow_3d is not None:
        evidence.append(f"近3日净流入={capital.main_net_inflow_3d:+.2e}")

    inflow = capital.main_net_inflow
    inflow_3d = capital.main_net_inflow_3d

    if inflow is not None and inflow > 0:
        if inflow_3d is not None and inflow_3d > 0:
            c.status = MASTER_BULLISH
            c.explanation = "主力资金连续净流入，资金面积极。"
            c.detail = f"当日主力净流入 {inflow:+.2e}，近3日累计净流入 {inflow_3d:+.2e}，资金持续流入，做多意愿较强。"
        else:
            c.status = MASTER_BULLISH
            c.explanation = "主力资金当日净流入，资金面向好。"
            c.detail = f"当日主力净流入 {inflow:+.2e}，资金面偏积极，关注后续持续性。"
    elif inflow is not None and inflow < 0:
        if inflow_3d is not None and inflow_3d < 0:
            c.status = MASTER_BEARISH
            c.explanation = "主力资金持续净流出，资金面偏空。"
            c.detail = f"当日主力净流出 {inflow:+.2e}，近3日累计净流出 {inflow_3d:+.2e}，资金持续流出，谨慎对待。"
        else:
            c.status = MASTER_NEUTRAL
            c.explanation = "主力资金当日净流出，需观察持续性。"
            c.detail = f"当日主力净流出 {inflow:+.2e}，单日流出暂不构成趋势，需关注后续几个交易日的情况。"
    else:
        c.status = MASTER_NEUTRAL
        c.explanation = "资金面中性，无明显方向。"
        c.detail = "当日主力资金净流入接近零，资金面暂无明显偏向。"

    evidence.append(f"资金评分={score}/100")
    c.evidence = evidence
    return c
