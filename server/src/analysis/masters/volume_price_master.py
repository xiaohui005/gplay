from src.analysis.datatypes import QuoteInput
from src.analysis.masters.base import (
    MASTER_BEARISH,
    MASTER_BULLISH,
    MASTER_INFO,
    MASTER_NEUTRAL,
    MasterConclusion,
)


def analyze_volume_price(quote: QuoteInput | None, score: int) -> MasterConclusion:
    c = MasterConclusion(code="volumePrice", name="量价大师")
    evidence: list[str] = []

    if quote is None or quote.volume_ratio is None or quote.change_percent is None:
        c.status = MASTER_INFO
        c.explanation = "量价数据不足，暂时无法进行量价分析。"
        c.detail = "缺少量比或涨跌幅数据，量价大师暂不生效。"
        evidence.append("数据不足：缺少成交量或行情数据")
        c.evidence = evidence
        return c

    vr = quote.volume_ratio
    cp = quote.change_percent
    evidence.append(f"量比={vr:.2f}  涨跌幅={cp:+.2f}%")

    if vr >= 1.5 and cp >= 3:
        c.status = MASTER_BULLISH
        c.explanation = "放量突破，量价配合良好。"
        c.detail = f"量比 {vr:.2f}（显著放量），涨幅 {cp:+.2f}%，典型的放量突破形态。如果突破关键阻力位，上涨空间有望打开。"
    elif vr >= 1.5 and cp >= 1.5:
        c.status = MASTER_BULLISH
        c.explanation = "放量上涨，买盘活跃。"
        c.detail = f"量比 {vr:.2f}，涨幅 {cp:+.2f}%，成交量放大配合价格上涨，市场参与度提升。"
    elif vr >= 1.3 and cp <= 0.5 and cp >= -0.5:
        c.status = MASTER_BEARISH
        c.explanation = "放量滞涨，资金有出货嫌疑。"
        c.detail = f"量比 {vr:.2f}（明显放量），但价格仅变动 {cp:+.2f}%，出现放量滞涨信号，需警惕主力资金出货。"
    elif vr >= 1.5 and cp < 0:
        c.status = MASTER_BEARISH
        c.explanation = "放量下跌，抛压较重。"
        c.detail = f"量比 {vr:.2f}，跌幅 {cp:+.2f}%，放量下跌说明抛压较大，短期可能继续下探。"
    elif vr <= 0.5 and cp >= 3:
        c.status = MASTER_BEARISH
        c.explanation = "缩量上涨，量价背离。"
        c.detail = f"量比 {vr:.2f}（明显缩量），涨幅 {cp:+.2f}%，量价背离信号。上涨缺乏成交量支撑，持续性存疑。"
    elif vr <= 0.7 and -1 <= cp <= 0:
        c.status = MASTER_BULLISH
        c.explanation = "缩量回踩，抛压减弱。"
        c.detail = f"量比 {vr:.2f}（缩量），涨跌幅 {cp:+.2f}%，缩量回调说明抛压减弱，如果关键支撑不破，是企稳信号。"
    elif vr <= 0.7 and cp > 0 and cp < 2:
        c.status = MASTER_NEUTRAL
        c.explanation = "缩量反弹，动能不足。"
        c.detail = f"量比 {vr:.2f}（缩量），涨幅 {cp:+.2f}%，反弹缺乏成交量配合，持续性有待观察。"
    else:
        c.status = MASTER_NEUTRAL
        c.explanation = "量价关系正常，无明显异常信号。"
        c.detail = f"量比 {vr:.2f}，涨跌幅 {cp:+.2f}%，量价配合正常，暂无线索。"
        if vr is not None:
            evidence.append(f"量比 {vr:.2f}，处于正常范围")

    evidence.append(f"量价评分={score}/100")
    c.evidence = evidence
    return c
