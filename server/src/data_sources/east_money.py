import json
import logging
import time
import urllib.request

logger = logging.getLogger(__name__)

# Sina 股票列表（免费，每次最多 ~100 条，需逐页翻取）
SINA_STOCK_LIST = (
    "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "Market_Center.getHQNodeData"
    "?page={page}&num=100&sort=code&asc=1&node=hs_a&symbol=&_s_r_a=init"
)

# East Money K 线
EM_KLINE = (
    "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    "?fields1=f1,f2,f3,f4,f5"
    "&fields2=f51,f52,f53,f54,f55,f56,f57"
    "&ut=7eea3edcaed734bea9c208c7c6a7f8d4"
    "&klt=101&fqt=1"
    "&secid={secid}&beg={date_from}&end={date_to}"
)


def _secid(symbol: str) -> str:
    return f"1.{symbol}" if symbol.startswith(("6", "9")) else f"0.{symbol}"


def fetch_stock_list() -> list[dict]:
    results = []
    page = 1
    empty_pages = 0
    while empty_pages < 3:
        url = SINA_STOCK_LIST.format(page=page)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            raw = resp.read().decode("gbk")
            items = json.loads(raw)
        except Exception as e:
            logger.warning("新浪股票列表第 %d 页失败: %s", page, e)
            empty_pages += 1
            page += 1
            time.sleep(1)
            continue

        if not items:
            empty_pages += 1
            page += 1
            time.sleep(0.5)
            continue

        empty_pages = 0
        for item in items:
            code = item.get("code", "")
            name = item.get("name", "")
            if not code or not name:
                continue
            market = "SSE" if code.startswith(("6", "9")) else "SZSE"
            if not any(r["symbol"] == code for r in results):
                results.append({"symbol": code, "name": name, "market": market})

        logger.info("新浪股票列表 第 %d 页: %d 条, 累计 %d", page, len(items), len(results))
        page += 1
        time.sleep(0.5)

    logger.info("新浪股票列表完成: 共 %d 只", len(results))
    return results


def fetch_kline(symbol: str, date_from: str = "20260101", date_to: str = "20260611") -> list[dict]:
    sid = _secid(symbol)
    url = EM_KLINE.format(secid=sid, date_from=date_from, date_to=date_to)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    raw = resp.read().decode("utf-8")
    body = json.loads(raw)
    klines = body.get("data", {}).get("klines", [])
    results = []
    for line in klines:
        parts = line.split(",")
        if len(parts) < 6:
            continue
        results.append({
            "date": parts[0],
            "open": _safe_float(parts, 1),
            "close": _safe_float(parts, 2),
            "high": _safe_float(parts, 3),
            "low": _safe_float(parts, 4),
            "volume": _safe_float(parts, 5),
            "amount": _safe_float(parts, 6),
        })
    logger.info("K线 [%s] %d 条", symbol, len(results))
    return results


def _safe_float(parts, idx, default=None):
    try:
        v = parts[idx].strip()
        return float(v) if v else default
    except (IndexError, ValueError, TypeError):
        return default
