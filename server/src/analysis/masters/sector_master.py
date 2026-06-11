from src.analysis.datatypes import SectorInput
from src.analysis.masters.base import (
    MASTER_BEARISH,
    MASTER_BULLISH,
    MASTER_INFO,
    MASTER_NEUTRAL,
    MasterConclusion,
)


def analyze_sector(sector: SectorInput | None, score: int) -> MasterConclusion:
    c = MasterConclusion(code="sector", name="板块大师")
    evidence: list[str] = []

    if sector is None:
        c.status = MASTER_INFO
        c.explanation = "板块数据尚未接入，暂时无法分析板块效应。"
        c.detail = "需要接入行业板块和概念板块数据后才能进行板块大师分析。"
        evidence.append("数据暂未接入：需授权板块数据")
        evidence.append(f"板块评分={score}/100（默认中性）")
        c.evidence = evidence
        return c

    name = sector.sector_name or "所属板块"
    evidence.append(f"板块名称={name}")

    if sector.sector_change_pct is not None:
        evidence.append(f"板块涨跌幅={sector.sector_change_pct:+.2f}%")

    if sector.sector_rank is not None:
        evidence.append(f"板块排名={sector.sector_rank}/行业")

    if sector.sector_change_pct is not None and sector.sector_change_pct > 2:
        c.status = MASTER_BULLISH
        c.explanation = f"{name} 板块表现强势，跑赢大盘。"
        c.detail = f"板块涨幅 {sector.sector_change_pct:+.2f}%，市场资金关注度高。"
    elif sector.sector_change_pct is not None and sector.sector_change_pct > 0:
        c.status = MASTER_BULLISH
        c.explanation = f"{name} 板块小幅上涨，表现尚可。"
        c.detail = f"板块涨幅 {sector.sector_change_pct:+.2f}%，处于温和上涨状态。"
    elif sector.sector_change_pct is not None and sector.sector_change_pct < -2:
        c.status = MASTER_BEARISH
        c.explanation = f"{name} 板块表现较弱，跑输大盘。"
        c.detail = f"板块跌幅 {sector.sector_change_pct:+.2f}%，整体偏弱，个股难独善其身。"
    elif sector.sector_change_pct is not None and sector.sector_change_pct < 0:
        c.status = MASTER_NEUTRAL
        c.explanation = f"{name} 板块小幅下跌，趋势偏弱。"
        c.detail = f"板块跌幅 {sector.sector_change_pct:+.2f}%，小幅回调需关注后续方向。"
    else:
        c.status = MASTER_NEUTRAL
        c.explanation = f"{name} 板块表现平稳。"
        c.detail = "板块无显著异动。"

    if sector.sector_rank is not None:
        if sector.sector_rank <= 10:
            c.status = MASTER_BULLISH if c.status != MASTER_BEARISH else c.status
            c.explanation += " 且板块排名靠前，属于当前主线方向。" if "主线" not in c.explanation else ""
        elif sector.sector_rank >= 80:
            c.explanation += " 板块排名靠后，属于弱势板块。"

    evidence.append(f"板块评分={score}/100")
    c.evidence = evidence
    return c
