# 个股新闻资讯与 K 线图表 — 设计文档

## 概述

在 GPlay 现有股票研判系统基础上，新增两个功能模块：
1. 个股新闻/资讯采集与展示
2. K 线数据持久化与前端图表

## 后端 — 新闻资讯

### 数据源
- 东方财富免费新闻 API：`https://push2.eastmoney.com/api/qt/stock/news/get?secid={secid}&count={count}`
- `secid` 格式与现有 K 线接口相同（1.{symbol} 沪/京，0.{symbol} 深）
- 返回标题、发布时间、摘要、原文链接

### 数据模型 `stock_news`
| 字段 | 类型 | 说明 |
|---|---|---|
| id | Integer PK | 自增主键 |
| symbol | String(16) | 股票代码 |
| title | String(512) | 新闻标题 |
| source | String(64) | 来源（如"东方财富"） |
| publish_time | DateTime | 发布时间 |
| url | String(1024) | 原文链接 |
| content_summary | Text | 摘要 |
| created_at | DateTime | 入库时间 |

去重策略：同 symbol + title + publish_time 不重复入库。

### 采集器
- `news_collector.py`：按 symbol 调用东方财富 API，解析 JSON 后写入 `stock_news`
- 触发方式：与一键采集（`POST /collect`）联动，采集行情/K 线后同时采集新闻

### API
```http
GET /api/stocks/{symbol}/news?limit=20
```
返回：
```json
{
  "items": [
    {
      "id": 1,
      "title": "...",
      "source": "东方财富",
      "publishTime": "2026-06-11T10:30:00",
      "url": "...",
      "contentSummary": "..."
    }
  ]
}
```

## 后端 — K 线持久化

### 数据模型 `stock_kline_daily`
| 字段 | 类型 | 说明 |
|---|---|---|
| id | Integer PK | 自增主键 |
| symbol | String(16) | 股票代码 |
| trade_date | String(10) | 交易日（YYYY-MM-DD） |
| open | Float | 开盘价 |
| high | Float | 最高价 |
| low | Float | 最低价 |
| close | Float | 收盘价 |
| volume | Float | 成交量（股） |
| amount | Float | 成交额（元） |

去重：同 symbol + trade_date 不重复入库（upsert）。

### 采集改造
- `kline_collector.py`：当前 `fetch_kline` 已有数据解析，新增入库逻辑
- 在 `POST /collect` 流程中，采集 K 线后写入 `stock_kline_daily`

### API
```http
GET /api/stocks/{symbol}/kline?days=60
```
返回：
```json
{
  "symbol": "600000",
  "items": [
    {
      "tradeDate": "2026-06-11",
      "open": 10.0,
      "high": 10.5,
      "low": 9.8,
      "close": 10.3,
      "volume": 1000000,
      "amount": 10000000
    }
  ]
}
```

## 前端 — K 线图

- 安装 `lightweight-charts` npm 包
- 新建组件 `KlineChart`，接收 `KlineBar[]` props
- 使用 `IChartApi.createChart` 创建图，`addCandlestickSeries` 渲染 K 线
- 支持周期切换：20日/60日/120日
- 位置：DetailPage 行情头部下方
- 响应式：窗口 resize 自动调整宽度

## 前端 — 新闻资讯

- 在 DetailPage 新增"相关资讯"卡片区域
- 显示新闻标题、来源名称、发布时间（相对时间）
- 点击整条跳转原文（新标签页）
- 无数据时显示"暂无相关资讯"
- 加载状态：骨架屏或 loading 文字

## 前后端 API 对接

| 前端调用 | 后端端点 | 说明 |
|---|---|---|
| `getKline(symbol, days)` | `GET /api/stocks/{symbol}/kline?days={days}` | 获取 K 线数据 |
| `getNews(symbol, limit)` | `GET /api/stocks/{symbol}/news?limit={limit}` | 获取新闻列表 |

## 测试

- 后端：`pytest tests/test_news.py` 测试新闻采集和 API
- 后端：`pytest tests/test_kline_api.py` 测试 K 线 API
- 前端：TypeScript 编译检查
