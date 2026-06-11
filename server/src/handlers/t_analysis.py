import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.data_sources.east_money import fetch_kline
from src.data_sources.tencent_quote import fetch_quote
from src.db.database import get_db
from src.models import StockBasic, StockQuoteSnapshot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stocks", tags=["t-analysis"])


def _ma(data: list[float], n: int) -> float | None:
    if len(data) < n:
        return None
    return round(sum(data[-n:]) / n, 2)


def _avg(vals: list[float]) -> float:
    return round(sum(vals) / len(vals), 4) if vals else 0


def _calc_atr(highs: list[float], lows: list[float], closes: list[float], n: int = 14) -> float:
    trs = []
    for i in range(1, len(closes)):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    relevant = trs[-n:] if len(trs) >= n else trs
    return _avg(relevant) if relevant else 0


def _calc_score(avg_amp: float, atr_pct: float, turnover: float | None,
                vol_ratio: float | None, volatility_trend: str) -> int:
    score = 0
    if avg_amp >= 3:
        score += 30
    elif avg_amp >= 2:
        score += 22
    elif avg_amp >= 1.2:
        score += 15
    elif avg_amp >= 0.6:
        score += 8
    else:
        score += 3

    if atr_pct >= 2.5:
        score += 20
    elif atr_pct >= 1.5:
        score += 15
    elif atr_pct >= 0.8:
        score += 10
    elif atr_pct >= 0.4:
        score += 5
    else:
        score += 2

    if turnover is not None:
        if turnover >= 5:
            score += 20
        elif turnover >= 3:
            score += 15
        elif turnover >= 1.5:
            score += 10
        elif turnover >= 0.5:
            score += 5
        else:
            score += 2

    if vol_ratio is not None:
        if vol_ratio >= 2:
            score += 15
        elif vol_ratio >= 1.3:
            score += 10
        elif vol_ratio >= 0.7:
            score += 5
        else:
            score += 2

    if volatility_trend == "expanding":
        score += 15
    elif volatility_trend == "stable":
        score += 10
    else:
        score += 5

    return min(score, 100)


def _suitability_label(score: int) -> str:
    if score >= 75:
        return "HIGHLY_SUITABLE"
    if score >= 55:
        return "SUITABLE"
    if score >= 35:
        return "GENERAL"
    return "UNSUITABLE"


@router.get("/{symbol}/t-analysis")
def t_analysis(symbol: str, db: Session = Depends(get_db)):
    basic = db.query(StockBasic).filter(StockBasic.symbol == symbol).first()
    if not basic:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 未找到")

    quote = db.query(StockQuoteSnapshot).filter(
        StockQuoteSnapshot.symbol == symbol
    ).order_by(StockQuoteSnapshot.id.desc()).first()
    live_quote = None
    try:
        live_quote = fetch_quote(symbol)
    except Exception as exc:
        logger.warning("实时行情 [%s] 获取失败，使用数据库快照: %s", symbol, exc)

    klines = sorted(fetch_kline(symbol), key=lambda k: k.get("date", ""))
    if not klines:
        return {
            "symbol": symbol,
            "name": basic.name,
            "suitability": "UNSUITABLE",
            "score": 0,
            "metrics": {
                "avgAmplitude5": 0,
                "avgAmplitude10": 0,
                "avgAmplitude20": 0,
                "atr": 0,
                "atrPercent": 0,
                "avgVolume5": None,
                "avgVolume20": None,
                "volumeRatio": None,
                "turnoverRate": quote.turnover_rate if quote else None,
                "volatilityTrend": "unknown",
            },
            "levels": {
                "ma5": None,
                "ma10": None,
                "ma20": None,
                "ma60": None,
                "currentPrice": (live_quote.get("latest_price") if live_quote else None) or (quote.latest_price if quote else 0),
            },
            "signals": {
                "buyPrice": 0,
                "sellPrice": 0,
                "stopLoss": 0,
                "expectedProfit": 0,
                "expectedProfitPct": 0,
                "riskAmount": 0,
                "riskPct": 0,
                "rewardRiskRatio": 0,
                "buyConditions": ["K线数据获取失败，无法计算买入条件"],
                "sellConditions": ["K线数据获取失败，无法计算卖出条件"],
            },
            "assessment": {
                "summary": f"{basic.name} K线数据获取失败，无法分析做T适用性",
                "strengths": [],
                "weaknesses": ["K线数据获取失败"],
                "suggestions": ["稍后重试或检查网络连接"],
            },
        }

    closes = [b["close"] for b in klines if b["close"] is not None]
    highs = [b["high"] for b in klines if b["high"] is not None]
    lows = [b["low"] for b in klines if b["low"] is not None]
    volumes = [b["volume"] for b in klines if b["volume"] is not None]
    latest_close = (live_quote.get("latest_price") if live_quote else None) or (quote.latest_price if quote and quote.latest_price else None) or (closes[-1] if closes else 0)
    if closes and latest_close:
        closes[-1] = latest_close
        if highs:
            highs[-1] = max(highs[-1], latest_close)
        if lows:
            lows[-1] = min(lows[-1], latest_close)

    amps_5 = [(h - l) / c * 100 for h, l, c in zip(highs[-5:], lows[-5:], closes[-5:])]
    amps_10 = [(h - l) / c * 100 for h, l, c in zip(highs[-10:], lows[-10:], closes[-10:])]
    amps_20 = [(h - l) / c * 100 for h, l, c in zip(highs[-20:], lows[-20:], closes[-20:])] if len(closes) >= 20 else amps_10

    avg_amp_5 = _avg(amps_5)
    avg_amp_10 = _avg(amps_10)
    avg_amp_20 = _avg(amps_20)

    atr = _calc_atr(highs, lows, closes)
    atr_pct = round(atr / latest_close * 100, 2) if latest_close else 0

    vol_5 = _avg(volumes[-5:]) if len(volumes) >= 5 else 0
    vol_20 = _avg(volumes[-20:]) if len(volumes) >= 20 else vol_5
    vol_ratio = round(vol_5 / vol_20, 2) if vol_20 else None

    if avg_amp_5 and avg_amp_10 and len(amps_10) >= 10:
        older_amp = _avg(amps_10[:-5]) if len(amps_10) > 5 else avg_amp_10
        if avg_amp_5 > older_amp * 1.1:
            vol_trend = "expanding"
        elif avg_amp_5 < older_amp * 0.9:
            vol_trend = "contracting"
        else:
            vol_trend = "stable"
    else:
        vol_trend = "stable"

    score = _calc_score(avg_amp_10, atr_pct, quote.turnover_rate if quote else None,
                        quote.volume_ratio if quote else None, vol_trend)
    label = _suitability_label(score)

    ma5 = _ma(closes, 5)
    ma10 = _ma(closes, 10)
    ma20 = _ma(closes, 20)
    ma60 = _ma(closes, 60)

    strengths = []
    weaknesses = []
    suggestions = []

    if avg_amp_10 >= 2:
        strengths.append(f"近10日平均振幅 {avg_amp_10:.1f}%，波动充足，适合做T")
    elif avg_amp_10 >= 1:
        strengths.append(f"近10日平均振幅 {avg_amp_10:.1f}%，有一定波动空间")
    else:
        weaknesses.append(f"近10日平均振幅仅 {avg_amp_10:.1f}%，波动不足，做T空间小")

    if atr_pct >= 1.5:
        strengths.append(f"ATR({atr_pct:.1f}%)波幅充足")
    elif atr_pct >= 0.5:
        weaknesses.append(f"ATR({atr_pct:.1f}%)偏低，单笔利润空间有限")
    else:
        weaknesses.append(f"ATR仅{atr_pct:.1f}%，做T收益难以覆盖成本")

    if quote and quote.turnover_rate:
        if quote.turnover_rate >= 3:
            strengths.append(f"换手率 {quote.turnover_rate:.1f}%，交投活跃")
        elif quote.turnover_rate >= 1:
            strengths.append(f"换手率 {quote.turnover_rate:.1f}%，流动性尚可")
        else:
            weaknesses.append(f"换手率 {quote.turnover_rate:.1f}%，流动性偏低")

    if vol_ratio is not None:
        if vol_ratio >= 1.5:
            strengths.append(f"近5日量比 {vol_ratio:.1f}，近期放量")
        elif vol_ratio < 0.7:
            weaknesses.append(f"近5日量比 {vol_ratio:.1f}，近期缩量")
        else:
            strengths.append(f"量比 {vol_ratio:.1f}，成交量平稳")

    if vol_trend == "expanding":
        strengths.append("波动率呈扩大趋势，短线机会增加")
    elif vol_trend == "contracting":
        weaknesses.append("波动率呈收缩趋势，短线机会减少")

    # 做T信号计算（按趋势方向区分）
    if latest_close >= (ma5 or latest_close):  # 上涨趋势：价格站上MA5
        buy_price = round(min(ma10, latest_close - atr) if ma10 else latest_close - atr, 2)
        sell_price = round(max(latest_close + atr * 0.5, ma5 or latest_close), 2)
        stop_loss = round(min(ma20 if ma20 else latest_close, latest_close - atr * 1.5), 2)
    else:  # 下跌趋势：价格在MA5下方
        buy_price = round(latest_close - atr * 0.5, 2)
        sell_price = round(min(ma5 or latest_close + atr, latest_close + atr * 0.5), 2)
        stop_loss = round(min(buy_price * 0.98, latest_close - atr), 2)
    # 确保止损价始终低于买入价，卖出价高于买入价
    buy_price = max(buy_price, round(latest_close * 0.95, 2))
    buy_price = min(buy_price, round(latest_close * 0.995, 2))
    stop_loss = round(max(min(stop_loss, buy_price * 0.99), buy_price * 0.98), 2)
    sell_price = max(sell_price, round(latest_close + atr * 0.5, 2))
    sell_price = max(sell_price, round(buy_price * 1.005, 2))  # 至少0.5%差价

    expected_profit = round(sell_price - buy_price, 2)
    expected_profit_pct = round(expected_profit / buy_price * 100, 2) if buy_price else 0
    risk_amount = round(buy_price - stop_loss, 2)
    risk_pct = round(risk_amount / buy_price * 100, 2) if buy_price else 0
    reward_risk = round(expected_profit / risk_amount, 2) if risk_amount > 0 else 0

    # 买入条件
    buy_conditions = []
    sell_conditions = []
    if score >= 35:
        buy_conditions.append(f"价格回调至{buy_price}附近（参考{('MA10' if latest_close >= (ma5 or latest_close) else 'ATR下轨')}）")
        buy_conditions.append("观察分时图缩量止跌后介入")
        buy_conditions.append(f"止损设在{stop_loss}下方，跌破离场")
        sell_conditions.append(f"反弹至{sell_price}附近（参考{('MA5压力' if latest_close >= (ma5 or latest_close) else 'ATR上轨')}）分批高抛")
        sell_conditions.append("分时图放量冲高回落时果断卖出")
        sell_conditions.append(f"预期收益 +{expected_profit_pct}% / 风险 {risk_pct}%，盈亏比 {reward_risk}")
    else:
        buy_conditions.append("当前不适合做T，观望为主")
        sell_conditions.append("有持仓可等待反弹至MA5附近减仓")

    if score >= 55:
        suggestions.append(f"适合做T，买入参考价{buy_price}附近，卖出参考价{sell_price}附近，止损{stop_loss}")
    elif score >= 35:
        suggestions.append("做T条件一般，需精选时机，等待波动扩大后再操作")
    else:
        suggestions.append("当前不适合做T，建议观望或选择波动更大的标的")

    suggestions.append(f"建议止损设在{stop_loss}以下，跌破离场")

    return {
        "symbol": symbol,
        "name": basic.name,
        "suitability": label,
        "score": score,
        "metrics": {
            "avgAmplitude5": avg_amp_5,
            "avgAmplitude10": avg_amp_10,
            "avgAmplitude20": avg_amp_20,
            "atr": round(atr, 3),
            "atrPercent": atr_pct,
            "avgVolume5": round(vol_5, 0) if vol_5 else None,
            "avgVolume20": round(vol_20, 0) if vol_20 else None,
            "volumeRatio": vol_ratio,
            "turnoverRate": quote.turnover_rate if quote else None,
            "volatilityTrend": vol_trend,
        },
        "levels": {
            "ma5": ma5,
            "ma10": ma10,
            "ma20": ma20,
            "ma60": ma60,
            "currentPrice": latest_close,
        },
        "signals": {
            "buyPrice": buy_price,
            "sellPrice": sell_price,
            "stopLoss": stop_loss,
            "expectedProfit": expected_profit,
            "expectedProfitPct": expected_profit_pct,
            "riskAmount": risk_amount,
            "riskPct": risk_pct,
            "rewardRiskRatio": reward_risk,
            "buyConditions": buy_conditions,
            "sellConditions": sell_conditions,
        },
        "assessment": {
            "summary": f"{basic.name} 做T综合评分 {score} 分（{label}）",
            "strengths": strengths,
            "weaknesses": weaknesses,
            "suggestions": suggestions,
        },
    }
