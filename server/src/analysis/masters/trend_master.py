from src.analysis.datatypes import KlineInput, QuoteInput
from src.analysis.masters.base import (
    MASTER_BEARISH,
    MASTER_BULLISH,
    MASTER_INFO,
    MASTER_NEUTRAL,
    MasterConclusion,
)


def analyze_trend(kline: KlineInput, quote: QuoteInput | None, score: int) -> MasterConclusion:
    c = MasterConclusion(code="trend", name="趋势大师")
    evidence: list[str] = []

    if kline.ma5 is not None and kline.ma10 is not None and kline.ma20 is not None:
        evidence.append(f"MA5={kline.ma5:.2f}  MA10={kline.ma10:.2f}  MA20={kline.ma20:.2f}")
        if kline.ma60 is not None:
            evidence.append(f"MA60={kline.ma60:.2f}")

    if quote and quote.latest_price is not None:
        evidence.append(f"最新价={quote.latest_price:.2f}")
        if quote.change_percent is not None:
            evidence.append(f"涨跌幅={quote.change_percent:+.2f}%")

    has_ma_data = kline.ma5 is not None

    if has_ma_data and quote and quote.latest_price is not None:
        above_ma5 = quote.latest_price >= kline.ma5
        above_ma10 = kline.ma10 is not None and quote.latest_price >= kline.ma10
        above_ma20 = kline.ma20 is not None and quote.latest_price >= kline.ma20
        above_ma60 = kline.ma60 is not None and quote.latest_price >= kline.ma60

        ma5v10 = kline.ma5 and kline.ma10 and kline.ma5 > kline.ma10
        ma10v20 = kline.ma10 and kline.ma20 and kline.ma10 > kline.ma20
        bullish_order = ma5v10 and ma10v20

        if above_ma5 and above_ma10 and above_ma20 and bullish_order:
            c.status = MASTER_BULLISH
            c.explanation = "价格站上所有短期均线，均线多头排列，上升趋势明确。"
            c.detail = f"收盘价 {quote.latest_price:.2f} 高于 MA5({kline.ma5:.2f})/MA10({kline.ma10:.2f})/MA20({kline.ma20:.2f})，且 MA5 > MA10 > MA20，均线多头排列。短期趋势强势，可延续看多。"
        elif above_ma5 and above_ma10 and above_ma20:
            c.status = MASTER_BULLISH
            c.explanation = "价格站上短期均线，但均线尚未完全多头排列。"
            c.detail = f"收盘价高于 MA5/MA10/MA20，但均线尚未形成 MA5 > MA10 > MA20 多头排列，趋势正在改善中。"
        elif above_ma5 and not above_ma20:
            c.status = MASTER_NEUTRAL
            c.explanation = "价格站上 MA5 但处于 MA20 下方，短期反弹中继。"
            c.detail = f"收盘价高于 MA5({kline.ma5:.2f}) 但低于 MA20({kline.ma20:.2f})，短期反弹，中期仍承压。"
        elif not above_ma20 and not above_ma60:
            c.status = MASTER_BEARISH
            c.explanation = "价格跌破 MA20 和 MA60，中期趋势偏弱。"
            c.detail = f"收盘价 {quote.latest_price:.2f} 低于 MA20({kline.ma20:.2f}) 和 MA60({kline.ma60:.2f})，中期趋势偏弱，注意下方支撑。"
        else:
            c.status = MASTER_NEUTRAL
            c.explanation = "均线交织，趋势尚不明确。"
            c.detail = "价格与均线关系复杂，趋势方向有待确认。"
    elif quote and quote.change_percent is not None:
        cp = quote.change_percent
        if cp >= 3:
            c.status = MASTER_BULLISH
            c.explanation = "当日涨幅较大，短期上涨动能强。"
            c.detail = f"当日涨幅 {cp:+.2f}%，短期动能强劲，注意成交量配合情况。"
        elif cp <= -3:
            c.status = MASTER_BEARISH
            c.explanation = "当日跌幅较大，短期下跌压力明显。"
            c.detail = f"当日跌幅 {cp:+.2f}%，短期承压，需关注下方支撑。"
        else:
            c.status = MASTER_NEUTRAL
            c.explanation = "价格窄幅波动，均线数据不足，趋势判断受限。"
            c.detail = "缺少均线数据，仅能根据当日涨跌幅做初步判断。"
    elif has_ma_data:
        c.status = MASTER_NEUTRAL
        c.explanation = "有均线数据但缺少最新行情，无法确认当前价格位置。"
        c.detail = "请等待最新行情数据更新后再做趋势判断。"
    else:
        c.status = MASTER_INFO
        c.explanation = "趋势数据不足，暂时无法判断趋势状态。"
        c.detail = "缺少均线和行情数据，趋势大师暂不生效。"
        evidence.append("数据不足：缺少 K 线均线和实时行情")

    if score >= 70:
        evidence.append(f"趋势评分={score}/100，偏强")
    elif score <= 35:
        evidence.append(f"趋势评分={score}/100，偏弱")
    else:
        evidence.append(f"趋势评分={score}/100，中性")

    c.evidence = evidence
    return c
