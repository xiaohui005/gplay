import json
import logging
import time
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)

EM_NEWS_SEARCH = (
    "https://search-api-web.eastmoney.com/search/jsonp"
    "?cb=jQuery&param={param}"
)


def _build_param(keyword: str, page: int = 1, page_size: int = 20) -> str:
    param = {
        "uid": "",
        "keyword": keyword,
        "type": ["cmsArticleWebOld"],
        "client": "web",
        "clientType": "web",
        "clientVersion": "curr",
        "param": {
            "cmsArticleWebOld": {
                "searchScope": "default",
                "sort": "default",
                "pageIndex": page,
                "pageSize": page_size,
                "preTag": "",
                "postTag": "",
            }
        },
    }
    return urllib.parse.quote(json.dumps(param, ensure_ascii=False))


def fetch_news(symbol: str, count: int = 20) -> list[dict]:
    param = _build_param(symbol, page_size=count)
    url = EM_NEWS_SEARCH.format(param=param)
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.eastmoney.com/",
    })

    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(req, timeout=15)
            raw = resp.read().decode("utf-8")
            text = raw.strip()
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                body = json.loads(text[start:end+1])
            else:
                logger.warning("新闻 [%s] 响应格式异常: %s", symbol, text[:200])
                return []
            break
        except Exception as e:
            if attempt < 2:
                logger.warning("新闻 [%s] 第 %d 次失败: %s，重试...", symbol, attempt + 1, e)
                time.sleep(1)
            else:
                logger.error("新闻 [%s] 3次重试均失败: %s", symbol, e)
                return []

    if body.get("code") != 0:
        logger.warning("新闻 [%s] API 返回错误: %s", symbol, body.get("msg", "未知错误"))
        return []

    articles = []
    result = body.get("result", {})
    for item in result.get("cmsArticleWebOld", []):
        title = item.get("title", "")
        if not title:
            continue
        articles.append({
            "title": title,
            "source": item.get("mediaName", "") or "东方财富",
            "publish_time": item.get("date", ""),
            "url": item.get("url", "") or "",
            "content_summary": item.get("content", "") or "",
        })

    logger.info("新闻 [%s] %d 条（搜索API）", symbol, len(articles))
    return articles
