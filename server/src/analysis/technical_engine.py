import logging
import math

logger = logging.getLogger(__name__)


def _ma(data: list[float], n: int) -> float | None:
    if len(data) < n:
        return None
    return sum(data[-n:]) / n


def _calc_macd(closes: list[float]) -> dict:
    """计算 MACD（简化版：12日EMA - 26日EMA）"""
    if len(closes) < 26:
        return {"histogram": 0, "direction": "neutral", "status": "neutral", "detail": "K线数据不足26根，无法计算MACD"}
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    dif = ema12[-1] - ema26[-1]
    offset = len(ema12) - len(ema26)
    dif_values = [ema12[i + offset] - ema26[i] for i in range(len(ema26))]
    dea = _ma(dif_values, 9)
    if dea is None:
        dea = 0
    histogram = dif - dea
    prev_hist = (ema12[-2] - ema26[-2]) - dea if len(ema12) > 1 and len(ema26) > 1 else histogram
    direction = "rising" if histogram > prev_hist else "falling"
    status = "bullish" if dif > dea and histogram > 0 else "bearish" if dif < dea and histogram < 0 else "neutral"
    return {
        "dif": round(dif, 4),
        "dea": round(dea, 4),
        "histogram": round(histogram, 4),
        "direction": direction,
        "status": status,
        "detail": f"MACD {'金叉多头' if status == 'bullish' else '死叉空头' if status == 'bearish' else '粘合'}"
    }


def _ema(data: list[float], n: int) -> list[float]:
    result = []
    multiplier = 2 / (n + 1)
    ema = sum(data[:n]) / n
    result.append(ema)
    for price in data[n:]:
        ema = (price - ema) * multiplier + ema
        result.append(ema)
    return result


def _calc_rsi(closes: list[float], n: int = 14) -> dict:
    if len(closes) < n + 1:
        return {"value": 50, "status": "neutral", "detail": "K线数据不足，RSI默认中性"}
    gains, losses = 0, 0
    for i in range(-n, 0):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / n
    avg_loss = losses / n
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    if rsi > 70:
        status = "overbought"
        detail = f"RSI {rsi:.1f}，超买区，注意回调风险"
    elif rsi < 30:
        status = "oversold"
        detail = f"RSI {rsi:.1f}，超卖区，关注反弹机会"
    else:
        status = "neutral"
        detail = f"RSI {rsi:.1f}，中性区间"
    return {"value": round(rsi, 1), "status": status, "detail": detail}


def _calc_bollinger(closes: list[float], n: int = 20) -> dict:
    if len(closes) < n:
        return {"position": "middle", "width": 0, "detail": "K线数据不足，无法计算布林带"}
    recent = closes[-n:]
    ma = sum(recent) / n
    variance = sum((x - ma) ** 2 for x in recent) / n
    std = math.sqrt(variance)
    upper = ma + 2 * std
    lower = ma - 2 * std
    latest = closes[-1]
    if latest >= upper:
        position = "upper"
        detail = "价格触及布林带上轨，偏强"
    elif latest <= lower:
        position = "lower"
        detail = "价格触及布林带下轨，偏弱"
    else:
        position = "middle"
        detail = "价格运行在布林带中轨附近"
    width = round((upper - lower) / ma * 100, 2) if ma else 0
    return {"position": position, "upper": round(upper, 2), "middle": round(ma, 2), "lower": round(lower, 2), "width": width, "detail": detail}


def _calc_volume_analysis(volumes: list[float], closes: list[float]) -> dict:
    if len(volumes) < 20:
        return {"volumeRatio": 1.0, "volumeTrend": "unknown", "priceVolumeConfirm": True, "detail": "量能数据不足"}
    vol_5 = sum(volumes[-5:]) / 5
    vol_20 = sum(volumes[-20:]) / 20
    vol_ratio = round(vol_5 / vol_20, 2) if vol_20 else 1.0
    vol_trend = "increasing" if vol_ratio > 1.3 else "decreasing" if vol_ratio < 0.7 else "stable"
    price_change = closes[-1] - closes[-5]
    confirm = (price_change > 0 and vol_ratio > 1) or (price_change < 0 and vol_ratio < 1)
    parts = []
    parts.append(f"量比 {vol_ratio}")
    parts.append("放量" if vol_ratio > 1.3 else "缩量" if vol_ratio < 0.7 else "量能平稳")
    parts.append("价量配合" if confirm else "价量背离")
    return {
        "volumeRatio": vol_ratio,
        "volumeTrend": vol_trend,
        "priceVolumeConfirm": confirm,
        "detail": "，".join(parts)
    }


def _calc_support_resistance(closes: list[float], highs: list[float], lows: list[float]) -> dict:
    if len(closes) < 10:
        return {"nearestSupport": 0, "nearestResistance": 0, "distanceToSupport": 0, "distanceToResistance": 0, "detail": "数据不足"}
    recent_high = max(highs[-10:])
    recent_low = min(lows[-10:])
    latest = closes[-1]
    dist_support = round((latest - recent_low) / latest * 100, 2) if latest else 0
    dist_resistance = round((recent_high - latest) / latest * 100, 2) if latest else 0
    return {
        "nearestSupport": round(recent_low, 2),
        "nearestResistance": round(recent_high, 2),
        "distanceToSupport": dist_support,
        "distanceToResistance": dist_resistance,
        "detail": f"近10日支撑 {recent_low}，压力 {recent_high}"
    }


def _calc_intraday_momentum(closes: list[float], highs: list[float], lows: list[float]) -> dict:
    if len(closes) < 2 or not highs or not lows:
        return {"status": "neutral", "changePercent": 0, "closePosition": 0, "detail": "日内动量数据不足"}
    prev_close = closes[-2]
    latest = closes[-1]
    high = highs[-1]
    low = lows[-1]
    change_pct = (latest - prev_close) / prev_close * 100 if prev_close else 0
    close_position = (latest - low) / (high - low) if high and low is not None and high > low else 0
    if change_pct >= 9.5 and close_position >= 0.85:
        status = "limit_up"
        detail = f"接近涨停强动量，涨幅 {change_pct:.2f}%，收在日内高位"
    elif change_pct >= 5 and close_position >= 0.75:
        status = "strong_up"
        detail = f"日内强势上涨，涨幅 {change_pct:.2f}%，收盘接近高位"
    elif change_pct <= -5 and close_position <= 0.25:
        status = "strong_down"
        detail = f"日内弱势下跌，跌幅 {change_pct:.2f}%，收盘接近低位"
    else:
        status = "neutral"
        detail = f"日内涨跌幅 {change_pct:.2f}%"
    return {
        "status": status,
        "changePercent": round(change_pct, 2),
        "closePosition": round(close_position, 2),
        "detail": detail,
    }


def _calc_atr_from_data(highs: list[float], lows: list[float], closes: list[float], n: int = 14) -> float:
    trs = []
    for i in range(1, len(closes)):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    relevant = trs[-n:] if len(trs) >= n else trs
    return sum(relevant) / len(relevant) if relevant else 0


def analyze_technical(klines: list[dict]) -> dict:
    klines = sorted(klines, key=lambda k: k.get("date", ""))
    closes = [b["close"] for b in klines if b.get("close") is not None]
    highs = [b["high"] for b in klines if b.get("high") is not None]
    lows = [b["low"] for b in klines if b.get("low") is not None]
    volumes = [b["volume"] for b in klines if b.get("volume") is not None]

    if len(closes) < 10:
        return _empty_result("K线数据不足10根，无法分析")

    latest_close = closes[-1]
    ma5 = _ma(closes, 5)
    ma10 = _ma(closes, 10)
    ma20 = _ma(closes, 20)

    # Trend
    if ma5 and ma10 and ma20:
        if ma5 > ma10 > ma20:
            trend_status = "bullish"
            trend_detail = "MA5 > MA10 > MA20 多头排列"
        elif ma5 < ma10 < ma20:
            trend_status = "bearish"
            trend_detail = "MA5 < MA10 < MA20 空头排列"
        else:
            trend_status = "neutral"
            trend_detail = "均线交叉，方向不明"
        if len(closes) >= 10:
            prev_ma5 = _ma(closes[:-1], 5) or 0
            prev_ma10 = _ma(closes[:-1], 10) or 0
            cross = "none"
            if prev_ma5 <= prev_ma10 and ma5 > ma10:
                cross = "golden_cross"
            elif prev_ma5 >= prev_ma10 and ma5 < ma10:
                cross = "death_cross"
        else:
            cross = "none"
    else:
        trend_status = "neutral"
        trend_detail = "均线数据不足"
        cross = "none"

    trend_vote = 1 if trend_status == "bullish" else (-1 if trend_status == "bearish" else 0)

    # Momentum
    macd = _calc_macd(closes)
    rsi = _calc_rsi(closes)
    macd_vote = 1 if macd["status"] == "bullish" else (-1 if macd["status"] == "bearish" else 0)
    rsi_vote = 1 if rsi["status"] == "oversold" else (-1 if rsi["status"] == "overbought" else 0)

    # Volatility
    bb = _calc_bollinger(closes)
    bb_vote = 1 if bb["position"] == "lower" else (-1 if bb["position"] == "upper" else 0)

    # Volume
    vol_analysis = _calc_volume_analysis(volumes, closes)
    vol_vote = 1 if (vol_analysis["priceVolumeConfirm"] and vol_analysis["volumeRatio"] > 1) else (-1 if not vol_analysis["priceVolumeConfirm"] else 0)

    # Support/Resistance
    sr = _calc_support_resistance(closes, highs, lows)
    sr_vote = 1 if sr["distanceToSupport"] < sr["distanceToResistance"] else (-1 if sr["distanceToResistance"] < sr["distanceToSupport"] else 0)

    # Intraday momentum
    intraday = _calc_intraday_momentum(closes, highs, lows)
    intraday_vote = 1 if intraday["status"] in {"limit_up", "strong_up"} else (-1 if intraday["status"] == "strong_down" else 0)

    # Composite scoring
    w_trend = trend_vote * 3
    w_macd = macd_vote * 1.5
    w_rsi = rsi_vote * 0.5
    w_bb = bb_vote * 1
    w_vol = vol_vote * 1.5
    w_sr = sr_vote * 1.5
    w_intraday = intraday_vote * (5 if intraday["status"] == "limit_up" else 2)

    total_weighted = w_trend + w_macd + w_rsi + w_bb + w_vol + w_sr + w_intraday
    max_possible = 3 + 1.5 + 0.5 + 1 + 1.5 + 1.5 + 5

    decision = decide_direction(total_weighted, max_possible)
    direction = decision["direction"]
    confidence = decision["confidence"]

    # Build evidence and risks
    key_evidence = []
    risk_warning = []
    if trend_status == "bullish":
        key_evidence.append(trend_detail)
    elif trend_status == "bearish":
        risk_warning.append(trend_detail)
    if cross == "golden_cross":
        key_evidence.append("MA5上穿MA10金叉")
    elif cross == "death_cross":
        risk_warning.append("MA5下穿MA10死叉")
    if macd["status"] == "bullish":
        key_evidence.append("MACD金叉多头")
    elif macd["status"] == "bearish":
        risk_warning.append("MACD死叉空头")
    if rsi["status"] == "overbought":
        risk_warning.append(rsi["detail"])
    elif rsi["status"] == "oversold":
        key_evidence.append(rsi["detail"])
    if bb["position"] == "upper":
        risk_warning.append("价格触及布林带上轨")
    elif bb["position"] == "lower":
        key_evidence.append("价格触及布林带下轨")
    if vol_analysis["priceVolumeConfirm"] and vol_analysis["volumeRatio"] > 1.3:
        key_evidence.append("价量配合，放量上涨")
    elif not vol_analysis["priceVolumeConfirm"] and vol_analysis["volumeRatio"] < 0.7:
        risk_warning.append("价量背离，缩量下跌")
    if intraday["status"] == "limit_up":
        key_evidence.append(intraday["detail"])
    elif intraday["status"] == "strong_up":
        key_evidence.append(intraday["detail"])
    elif intraday["status"] == "strong_down":
        risk_warning.append(intraday["detail"])

    if not key_evidence:
        key_evidence.append("各指标信号不明确，市场方向待确认")
    if not risk_warning:
        risk_warning.append("当前无明显风险信号")

    # Summary
    dir_map = {"UP": "看涨↑", "DOWN": "看跌↓", "SIDEWAYS": "盘整→"}
    summary_parts = [f"综合研判：{dir_map.get(direction, '中性')}，信心度{confidence:.0f}%"]
    if direction == "UP":
        summary_parts.append("多项指标共振偏多" if total_weighted > 4 else "部分指标偏多，但信号强度一般")
    elif direction == "DOWN":
        summary_parts.append("多项指标共振偏空" if total_weighted < -4 else "部分指标偏空，但信号强度一般")
    else:
        summary_parts.append("多空力量接近，按当前权重给出方向判断")
    summary_parts.append(f"趋势{trend_detail}，{macd['detail']}，{rsi['detail']}，{bb['detail']}，{vol_analysis['detail']}，{intraday['detail']}")

    # Compute buy/sell prices based on current price + ATR, not old support/resistance
    atr_val = _calc_atr_from_data(highs, lows, closes)
    if direction == "UP":
        buy_price = round(latest_close, 2)
        sell_price = round(latest_close + atr_val, 2)
        stop_loss = round(latest_close - atr_val * 0.5, 2)
        recommendation = "适合买入"
    elif direction == "DOWN":
        buy_price = round(latest_close - atr_val * 0.5, 2)
        sell_price = round(latest_close, 2)
        stop_loss = round(latest_close + atr_val * 0.5, 2)
        recommendation = "适合卖出"
    else:
        buy_price = round(latest_close - atr_val * 0.3, 2)
        sell_price = round(latest_close + atr_val * 0.3, 2)
        stop_loss = round(latest_close - atr_val * 0.8, 2)
        recommendation = "适合买入" if direction == "UP" else "适合卖出"
    # Ensure sane ordering: stop < buy < sell (for UP) or buy < sell < stop (for DOWN)
    if direction == "UP":
        stop_loss = min(stop_loss, buy_price * 0.97)
        sell_price = max(sell_price, buy_price * 1.005)
    elif direction == "DOWN":
        stop_loss = max(stop_loss, sell_price * 1.03)
        buy_price = min(buy_price, sell_price * 0.995)

    return apply_confidence_floor(
        direction=direction,
        confidence=confidence,
        recommendation=recommendation,
        summary="；".join(summary_parts),
        payload={
            "signals": {
                "buyPrice": buy_price,
                "sellPrice": sell_price,
                "stopLoss": stop_loss,
            },
            "keyEvidence": key_evidence,
            "riskWarning": risk_warning,
            "indicators": {
                "trend": {
                    "maAlignment": trend_status,
                    "maCross": cross,
                    "ma5": round(ma5, 2) if ma5 else None,
                    "ma10": round(ma10, 2) if ma10 else None,
                    "ma20": round(ma20, 2) if ma20 else None,
                    "detail": trend_detail,
                },
                "momentum": {
                    "macd": macd,
                    "rsi": rsi,
                },
                "volatility": bb,
                "volume": vol_analysis,
                "supportResistance": sr,
                "intradayMomentum": intraday,
            },
        },
    )


def apply_confidence_floor(direction: str, confidence: float, recommendation: str, summary: str, payload: dict | None = None) -> dict:
    result = {
        "direction": direction,
        "confidence": confidence,
        "recommendation": recommendation,
        "summary": summary,
    }
    if payload:
        result.update(payload)
    return result


def decide_direction(total_weighted: float, max_possible: float) -> dict:
    direction = "UP" if total_weighted >= 0 else "DOWN"
    confidence = min(abs(total_weighted) / max_possible * 100, 100) if max_possible else 0
    return {"direction": direction, "confidence": round(max(confidence, 50), 0)}


def _empty_result(reason: str) -> dict:
    return {
        "direction": "SIDEWAYS",
        "confidence": 0,
        "recommendation": "建议观望",
        "signals": {"buyPrice": 0, "sellPrice": 0, "stopLoss": 0},
        "summary": reason,
        "keyEvidence": [],
        "riskWarning": [reason],
        "indicators": {
            "trend": {"maAlignment": "neutral", "maCross": "none", "ma5": None, "ma10": None, "ma20": None, "detail": reason},
            "momentum": {"macd": {"histogram": 0, "direction": "neutral", "status": "neutral", "detail": reason}, "rsi": {"value": 50, "status": "neutral", "detail": reason}},
            "volatility": {"position": "middle", "width": 0, "detail": reason},
            "volume": {"volumeRatio": 1.0, "volumeTrend": "unknown", "priceVolumeConfirm": True, "detail": reason},
            "supportResistance": {"nearestSupport": 0, "nearestResistance": 0, "distanceToSupport": 0, "distanceToResistance": 0, "detail": reason},
        },
    }
