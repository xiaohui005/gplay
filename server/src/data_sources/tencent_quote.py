import logging
import re
import urllib.request

logger = logging.getLogger(__name__)

TENCENT_URL = "http://qt.gtimg.cn/q={market}{code}"

MARKET_MAP = {
    "sh": "1",  # 上海
    "sz": "0",  # 深圳
    "bj": "2",  # 北京
}


def _detect_market(code: str) -> str:
    code = code.strip()
    if code.startswith(("6", "9")):
        return "sh"
    if code.startswith(("0", "2", "3")):
        return "sz"
    if code.startswith(("4", "8")):
        return "bj"
    return "sh"


def fetch_quote(symbol: str) -> dict:
    market = _detect_market(symbol)
    url = TENCENT_URL.format(market=market, code=symbol)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=10)
    text = resp.read().decode("gbk")

    # Parse: v_sh600000="1~name~code~..."
    # Use regex to extract the string between quotes after the first =
    m = re.search(r'"(.+)"', text)
    if not m:
        raise ValueError(f"无法解析腾讯行情响应: {text[:200]}")

    fields = m.group(1).split("~")
    if len(fields) < 45:
        raise ValueError(f"字段数不足: {len(fields)}")

    volume_lots = _safe_float(fields, 6, 0.0)  # 手
    amount_wan = _safe_float(fields, 7, 0.0)   # 万元
    pre_close = _safe_float(fields, 4)
    current = _safe_float(fields, 3)
    change_pct = ((current - pre_close) / pre_close * 100) if pre_close and pre_close != 0 else 0.0

    data = {
        "symbol": symbol,
        "name": fields[1],
        "latest_price": current,
        "change_percent": round(change_pct, 2),
        "open": _safe_float(fields, 5),
        "pre_close": pre_close,
        "high": _safe_float(fields, 33),
        "low": _safe_float(fields, 34),
        "volume": int(volume_lots * 100),           # 手 → 股
        "amount": int(amount_wan * 10000),           # 万元 → 元
        "bid_price": _safe_float(fields, 9),
        "ask_price": _safe_float(fields, 19),
        "datetime_str": fields[30],
    }

    logger.info("腾讯行情 [%s] %s  %.2f  %.2f%%", symbol, data["name"], current, change_pct)
    return data


def _safe_float(fields, idx, default=None):
    try:
        val = fields[idx].strip()
        return float(val) if val else default
    except (IndexError, ValueError, TypeError):
        return default
