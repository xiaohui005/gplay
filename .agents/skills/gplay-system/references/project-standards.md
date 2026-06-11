# GPlay 项目标准记录

## 当前状态

- 项目目录：`D:\gongju\gplay`
- 技术栈：Python 3.13.5 + FastAPI + SQLAlchemy + APScheduler (后端)，Vite + React + TypeScript + react-router-dom (前端)
- 数据库：SQLite（开发），通过 `DATABASE_URL` 环境变量可切换 PostgreSQL
- 后端目录：`D:\gongju\gplay\server`，入口 `src/main.py`
- 前端目录：`D:\gongju\gplay\frontend`，入口 `src/main.tsx`

## 端口

| 服务 | 端口 | 备注 |
|---|---|---|
| 后端 (FastAPI) | 8008 | |
| 前端 (Vite dev) | 5173 | proxy /api → localhost:8008 |

## 命令

| 动作 | 工作目录 | 命令 |
|---|---|---|
| 启动后端 | `server/` | `python -m src.main` |
| 启动前端 dev | `frontend/` | `npx vite --host` |
| 前端 TypeScript 检查 | `frontend/` | `npx tsc --noEmit` |
| 前端生产打包 | `frontend/` | `npx tsc --noEmit; npx vite build` |
| 运行后端测试 | `server/` | `python -m pytest` |
| 运行单测文件 | `server/` | `python -m pytest tests/test_xxx.py -v` |
| 种子数据 | `server/` | `python -m src.seed` |
| 后端重启 | `server/` | 先 kill 旧进程，再 `python -m src.main` |

## 后端关键端点

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/stocks/search?keyword=...&limit=...` | 搜索股票（代码前缀/名称模糊/拼音模糊） |
| GET | `/api/stocks/{symbol}/analysis` | 获取完整研判结果（评分、大师建议、条件、买卖计划、复盘） |
| POST | `/api/stocks/{symbol}/collect` | 一键采集（腾讯行情 + 东方财富K线 + 东方财富新闻），直接写入标准表 |
| GET | `/api/stocks/{symbol}/quote` | 获取最新行情快照 |
| GET | `/api/stocks/{symbol}/kline?days=60` | 获取K线数据（日K，含日期/OHLC/成交量/成交额） |
| GET | `/api/stocks/{symbol}/news?limit=20` | 获取个股相关新闻资讯 |
| GET | `/api/watchlist` | 获取关注列表（含最新价、涨跌幅） |
| POST | `/api/watchlist/{symbol}` | 添加关注 |
| DELETE | `/api/watchlist/{symbol}` | 取消关注 |
| GET | `/api/stocks/search-full` | 管理后台全量搜索 |
| GET | `/` | 服务信息（含可用端点列表） |

## 数据源

| 数据 | 来源 | source_code |
|---|---|---|
| 实时行情 | Tencent Finance `qt.gtimg.cn` | `tencent_free` |
| 股票列表 | Sina `vip.stock.finance.sina.com.cn` | `east_money_free` |
| K线 | East Money `push2his.eastmoney.com` | `east_money_free` |
| 新闻资讯 | East Money `push2.eastmoney.com/api/qt/stock/news/get` | `east_money_free` |

## 关键约定

- `symbol` 以裸代码格式存储（如 `"000630"`），不带市场前缀，`market` 字段单独存储（`SSE`/`SZSE`/`BSE`）
- 前端 proxy `/api` → `http://localhost:8008` 在 `vite.config.ts` 中配置
- 一键采集端点 `POST /collect` 绕过 `raw_market_data` 管道，直接写入 `stock_basic` + `stock_quote_snapshot` 标准表
- 前端处理行情 404：显示"尚未采集" + 采集按钮
- 前端搜索页处理未入库股票：显示"数据库中暂无该股票" + 采集按钮
- SUSPENDED/DELISTED 股票跳过评分，直接返回 HOLD/AVOID
- BUY_LIGHT/BUY_WATCH 建议必须附带止损条件
- data_sources 限流策略：腾讯接口不做控制，Sina 页间睡 0.5s，东方财富 K线 502 时重试

## 前端关键文件

| 文件 | 用途 |
|---|---|
| `src/pages/SearchPage.tsx` | 搜索页：300ms 防抖、拼音支持、未入库一键采集、关注面板、关注按钮 |
| `src/pages/DetailPage.tsx` | 详情页：行情头、K线图、评分网格、大师建议、买卖计划、相关资讯、采集/刷新按钮、关注按钮 |
| `src/components/KlineChart.tsx` | K 线图表组件（lightweight-charts，支持周期切换，含成交量柱） |
| `src/api/client.ts` | API 请求封装（get/post/del helper + searchStocks, getQuote, getAnalysis, getKline, getNews, collectStock, getWatchlist, addWatchlist, removeWatchlist）|
| `src/types/api.ts` | TypeScript 类型定义（StockItem, StockQuote, AnalysisResult, ScoreBlock, MasterGuidance, WatchlistItem, KlineBar, NewsItem）|

## 数据模型

| 表 | 用途 |
|---|---|
| `stock_basic` | 股票基本信息（symbol, name, market, trade_status, pinyin, list_date, total_shares） |
| `stock_quote_snapshot` | 行情快照（latest_price, change_percent, volume, amount, turnover_rate, volume_ratio 等） |
| `stock_kline_daily` | 日K线数据（symbol, trade_date, open, high, low, close, volume, amount，唯一约束 symbol+trade_date） |
| `stock_news` | 股票相关新闻（symbol, title, source, publish_time, url, content_summary，唯一约束 symbol+title+publish_time） |
| `analysis_result` | 分析结果（score, suggestion, master_detail, upside_conditions 等） |
| `raw_market_data` | 原始市场数据管道（预留，当前一键采集跳过此表） |
| `user_watchlist` | 用户关注列表（symbol, added_at） |

## 已知限制 / 待办

| 问题 | 状态 |
|---|---|
| 资金、板块、基本面数据尚未接入 | 未开始 |
| 事件数据尚未接入 | 未开始 |
| 分笔/Level2/盘口数据 | 未开始 |
| `datetime.utcnow()` 废弃警告 → 改为 `datetime.now(UTC)` | 未处理 |
| FastAPI `@app.on_event` 废弃 → 改为 lifespan | 未处理 |
| K线图表已在前端展示（lightweight-charts，支持20/60/120日切换） | 已完成 |
| 个股新闻资讯已接入采集与展示 | 已完成 |
| 生产 PostgreSQL 切换 | 简单（改 .env 的 DATABASE_URL）|
