import json
import logging
import time
import urllib.request

logger = logging.getLogger(__name__)

EM_NEWS_URL = (
    "https://push2.eastmoney.com/api/qt/stock/news/get"
    "?fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13"
    "&fields2=f51,f52,f53,f54,f55"
    "&ut=7eea3edcaed734bea9c208c7c6a7f8d4"
    "&secid={secid}&count={count}"
)


def _secid(symbol: str) -> str:
    return f"1.{symbol}" if symbol.startswith(("6", "9")) else f"0.{symbol}"


def fetch_news(symbol: str, count: int = 20) -> list[dict]:
    secid = _secid(symbol)
    url = EM_NEWS_URL.format(secid=secid, count=count)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://guba.eastmoney.com/",
    })

    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            raw = resp.read().decode("utf-8")
            body = json.loads(raw)
            break
        except Exception as e:
            if attempt < 2:
                logger.warning("新闻 [%s] 第 %d 次失败: %s，重试...", symbol, attempt + 1, e)
                time.sleep(1)
            else:
                logger.error("新闻 [%s] 3次重试均失败: %s", symbol, e)
                return []

    data = body.get("data", {})
    articles = []
    for item in data.get("list", []):
        title = item.get("f51", "") or item.get("title", "")
        if not title:
            continue
        articles.append({
            "title": title,
            "source": item.get("f52") or item.get("source", "") or "东方财富",
            "publish_time": item.get("f53") or item.get("date", ""),
            "url": item.get("f54") or item.get("url", "") or "",
            "content_summary": item.get("f55") or item.get("content", "") or "",
        })

    logger.info("新闻 [%s] %d 条", symbol, len(articles))
    return articles
