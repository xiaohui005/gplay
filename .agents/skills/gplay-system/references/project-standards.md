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
| 前端生产版 | 8008 | 后端直接托管 `frontend/dist`，无需常开 5173 |

## 命令

| 动作 | 工作目录 | 命令 |
|---|---|---|
| 启动后端 | `server/` | `python -m uvicorn src.main:app --port 8008` |
| 启动前端 dev（交互式终端） | `frontend/` | `npx vite --host` |
| 启动前端 dev（Start-Process） | `frontend/` | `Start-Process -FilePath "node_modules/.bin/vite" -ArgumentList "--host","--port","5173"` |
| 前端 TypeScript 检查 | `frontend/` | `npx tsc --noEmit` |
| 前端生产打包 | `frontend/` | `npx tsc --noEmit; npx vite build` |
| 后端托管前端 | `frontend/` + `server/` | 先 `npm run build`，再启动/重启后端，访问 `http://127.0.0.1:8008/` |
| 一键隐藏重启后端 | 项目根目录 | 双击 `启动后端-隐藏.vbs`（完全无黑窗）或 `启动后端.bat`（快速调用 VBS 后退出） |
| 运行后端测试 | `server/` | `python -m pytest` |
| 运行单测文件 | `server/` | `python -m pytest tests/test_xxx.py -v` |
| 种子数据 | `server/` | `python -m src.seed` |
| 后端重启 | `server/` | 先 kill 旧进程，再 `python -m uvicorn src.main:app --port 8008` |

## 后端关键端点

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/stocks/search?keyword=...&limit=...` | 搜索股票（代码前缀/名称模糊/拼音模糊） |
| GET | `/api/stocks/{symbol}/analysis` | 获取完整研判结果（评分、大师建议、条件、买卖计划、复盘） |
| POST | `/api/stocks/{symbol}/collect` | 一键采集（腾讯行情 + 东方财富K线 + 东方财富新闻），直接写入标准表 |
| POST | `/api/stocks/{symbol}/collect-news` | 仅采集个股新闻资讯，不采集行情或K线 |
| GET | `/api/stocks/{symbol}/quote` | 获取最新行情快照 |
| GET | `/api/stocks/{symbol}/kline?days=60` | 获取K线数据（日K，含日期/OHLC/成交量/成交额） |
| GET | `/api/stocks/{symbol}/news?limit=20` | 获取个股相关新闻资讯 |
| GET | `/api/watchlist` | 获取关注列表（含最新价、涨跌幅） |
| POST | `/api/watchlist/{symbol}` | 添加关注 |
| DELETE | `/api/watchlist/{symbol}` | 取消关注 |
| GET | `/api/stocks/search-full` | 管理后台全量搜索 |
| GET | `/api/stocks/{symbol}/t-analysis` | 做T分析（评分 + Metrics + 信号） |
| GET | `/api/stocks/{symbol}/technical-analysis` | 技术研判（方向、信心度、信号价、证据/风险） |
| POST | `/api/stocks/{symbol}/technical-analysis` | 保存技术研判到历史（含早盘/收盘前研判时段） |
| GET | `/api/stocks/technical-analysis/history` | 技术研判历史（含准确率统计） |
| GET | `/api/settings/notification` | 读取通知配置（Bark 配置） |
| PUT | `/api/settings/notification` | 保存通知配置（Bark 启用、服务地址、Device Key） |
| POST | `/api/settings/notification/test` | 发送 Bark 测试推送 |
| GET | `/api` | 服务信息（含可用端点列表） |
| GET | `/` | 前端生产页面（返回 `frontend/dist/index.html`） |

## 数据源

| 数据 | 来源 | source_code |
|---|---|---|
| 实时行情 | Tencent Finance `qt.gtimg.cn` | `tencent_free` |
| 股票列表 | Sina `vip.stock.finance.sina.com.cn` | `east_money_free` |
| K线 | Sina `money.finance.sina.com.cn`（`scale=240` 日线） | `east_money_free` |
| 新闻资讯 | East Money `search-api-web.eastmoney.com/search/jsonp` | `east_money_free` |

## 关键约定

- `symbol` 以裸代码格式存储（如 `"000630"`），不带市场前缀，`market` 字段单独存储（`SSE`/`SZSE`/`BSE`）
- 前端 proxy `/api` → `http://localhost:8008` 在 `vite.config.ts` 中配置
- 一键采集端点 `POST /collect` 绕过 `raw_market_data` 管道，直接写入 `stock_basic` + `stock_quote_snapshot` 标准表；仅资讯采集使用 `POST /collect-news`，只写入 `stock_news`
- 前端处理行情 404：显示"尚未采集" + 采集按钮
- 前端搜索页处理未入库股票：显示"数据库中暂无该股票" + 采集按钮
- SUSPENDED/DELISTED 股票跳过评分，直接返回 HOLD/AVOID
- BUY_LIGHT/BUY_WATCH 建议必须附带止损条件
- data_sources 限流策略：腾讯接口不做控制，Sina 页间睡 0.5s，Sina K线无重试直接回调（East Money 区域不可达，已切换为 Sina）
- East Money `push2his.eastmoney.com` / `push2.eastmoney.com` 在该环境不可达（`Remote end closed connection`），相关代码保留但标记废弃
- 技术研判历史硬约束：每只股票每天最多 2 条，`10:00` 早盘研判 1 条、`14:30` 收盘前研判 1 条；同日同股票同时段再次保存只能更新原记录，不能新增重复记录
- 技术研判自动保存只针对关注列表 `user_watchlist`，不扫全市场；页面预览不入历史，点击保存或定时任务才写入历史
- 技术研判历史验证口径：新增研判只返回 `UP`/`DOWN`；早盘 `10:00` 用当日收盘验证，收盘前 `14:30` 用次日 `10:00` 附近快照验证，缺少验证价保持 `待验证`；准确率只统计 `命中`/`未命中`
- 技术研判/做T指标计算必须先将 K 线按 `date` 升序排序，再使用 `closes[-1]` 作为最新价；做T价位必须贴近当前价，不能用旧 MA 产生远离现价的买卖点
- Bark 推送第一版只做配置页和测试推送，不自动根据行情/新闻/技术研判触发；配置保存在 `notification_config` 表，后端接口统一在 `/api/settings/notification` 下。
- FastAPI 8008 直接托管前端生产包：`/assets/*` 返回静态资源，非 `/api/*` 路径回退到 `frontend/dist/index.html`，支持 React Router 深链接；服务信息改到 `/api`

## 前端关键文件

| 文件 | 用途 |
|---|---|
| `src/pages/SearchPage.tsx` | 搜索页：300ms 防抖、拼音支持、未入库一键采集、关注面板、关注按钮 |
| `src/pages/DetailPage.tsx` | 详情页：行情头、K线图、评分网格、大师建议、买卖计划、相关资讯、采集/刷新按钮、关注按钮 |
| `src/pages/TechnicalAnalysisPage.tsx` | 技术研判页：方向、信号强度、信号通知、买卖止损、指标网格、证据/风险 |
| `src/pages/AnalysisHistoryPage.tsx` | 技术研判历史页：历史记录、准确率、验证结果 |
| `src/pages/SettingsPage.tsx` | 系统配置页：Bark 启用、服务地址、Device Key、保存配置、测试推送 |
| `src/components/KlineChart.tsx` | K 线图表组件（lightweight-charts，支持周期切换，含成交量柱） |
| `src/api/client.ts` | API 请求封装（get/post/put/del helper + 股票、关注、技术研判、通知配置 API）|
| `src/types/api.ts` | TypeScript 类型定义（股票、行情、研判、关注、K线、新闻、技术研判、通知配置类型）|

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
| `notification_config` | 通知配置（Bark 启用、服务地址、Device Key） |

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

## 已知工程陷阱

| 问题 | 症状 | 原因 | 修复 |
|---|---|---|---|
| KlineChart 销毁后残留 ref | `Object is disposed` + 详情页白屏 | React StrictMode 双挂载时 useEffect cleanup 只调了 `remove()` 没置 null，第二次进入 buildChart 时 `chartRef.current.remove()` 对已销毁对象调用 | cleanup 中 `remove()` 后把所有 ref 置 null |
| East Money API 不可达 | 采集/分析卡住 8s+ 后返回空 | 机器 IP 被 East Money 区域限制 | 切到 Sina K线 API |
| 做T信号止损价高于买入价 | 盈亏比负数 | 下跌趋势中 MA20 > 当前价，止损取 MA20 导致在买入价之上 | 按趋势方向区分：上涨用 MA，下跌用 ATR，并强制 `stop < buy < sell` |
| `Start-Process` 启动 `npx` 进程会立即退出 | 前端 dev server 启动后秒死 | `npx` 执行时需要下载/交互，Start-Process 的 Hidden 窗口不适合 | 直接用 `node_modules/.bin/vite` 路径绕过 npx |
| 技术研判取到 K 线旧数据 | 买卖价远离现价 | K 线顺序与指标计算假设不一致，旧 close 被当成当前价 | 计算前按 `date` 升序排序，再用 `closes[-1]` / `klines[-1]["close"]` 取最新价 |
| 做T买卖价远离现价 | 当前价 27.57 却给 17.x 买入价 | K 线顺序和指标计算方向不一致，旧价/旧均线被当成当前参考 | 做T内部按日期升序排序，并限制买入价贴近当前价 |
