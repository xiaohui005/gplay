---
name: technical-analysis-workflow
description: Use when changing GPlay 技术研判、研判历史、自动调度、准确率验证、信心度解释、信号价、技术指标计算或相关 API/页面展示。
---

# Technical Analysis Workflow

## 使用时机

Use when:

- 修改技术研判页、研判历史页或相关样式。
- 修改做T分析页、做T信号价或做T评分逻辑。
- 调整 `UP`/`DOWN` 方向、信心度、推荐语、信号通知。
- 修改买入价、卖出价、止损价或 ATR/支撑压力相关逻辑。
- 调整技术指标计算、证据列表、风险提示、研判历史、命中率或自动调度。
- 排查技术研判页面白屏、加载卡住、价格远离现价、信号解释不清楚。

## 关键文件

| 层 | 文件 | 用途 |
|---|---|---|
| 指标引擎 | `server/src/analysis/technical_engine.py` | 计算趋势、MACD、RSI、布林带、量能、支撑压力、方向和信心度 |
| 做T处理器 | `server/src/handlers/t_analysis.py` | 计算做T评分、当前价、买入价、卖出价、止损价 |
| API 处理器 | `server/src/handlers/technical_analysis.py` | 拉取 K 线、生成记录、返回详情/历史/验证结果 |
| 调度器 | `server/src/services/task_scheduler.py` | `10:00`/`14:30` 自动采集并保存关注股技术研判 |
| 数据模型 | `server/src/models/technical_record.py` | 存储研判记录、信心度、方向、指标 JSON、验证结果 |
| 类型 | `frontend/src/types/api.ts` | `TechnicalAnalysisResult` 和指标结构 |
| 页面 | `frontend/src/pages/TechnicalAnalysisPage.tsx` | 技术研判详情、信号通知、证据/风险展示 |
| 历史 | `frontend/src/pages/AnalysisHistoryPage.tsx` | 历史记录、表格搜索、准确率、验证状态 |
| 样式 | `frontend/src/styles/technical-analysis.css` | 技术研判页面样式 |

## 标准流程

### 1. 先确认数据含义

- `direction` 是综合方向：`UP` 看涨、`DOWN` 看跌；新增研判不得再输出 `SIDEWAYS`。
- `confidence` 不是涨跌概率，是技术指标对当前方向的一致程度。
- 低信心度方向要解释成“轻微偏向”，不能展示成强买/强卖。
- `recommendation` 是操作倾向，必须和信号价排序一致。
- 技术研判按每天两波记录：`10:00` 早盘研判、`14:30` 收盘前研判。
- 打开页面只做预览，点击保存或定时任务才写入历史，历史中同时保留研判时段和实际保存时间。
- 自动保存只针对关注列表股票，`10:00` 和 `14:30` 各执行一次。
- 每只股票每天最多 2 条历史：早盘 1 条、收盘前 1 条；同日同股票同时段再次保存必须更新原记录，不能新增重复记录。

### 2. 保持价格来源正确

- `fetch_kline()` 返回顺序可能与指标算法假设不一致，进入技术研判/做T计算前必须按 `date` 升序排序。
- 排序后才允许用 `closes[-1]` / `klines[-1]["close"]` 当最新价。
- 不要在未排序 K 线上遍历或取最后一个 close，否则会取到旧 K 线。
- 技术指标可以用完整 K 线序列，当前操作价必须基于最新价。
- 做T价位必须贴近当前价，买入价不能因为旧 MA/旧支撑位偏离现价太远。

### 3. 保持信号价顺序

| 方向 | 约束 |
|---|---|
| `UP` | `stopLoss < buyPrice < sellPrice` |
| `DOWN` | `buyPrice < sellPrice < stopLoss` |
| 低信心度 | 价格只作为弱信号参考，不应显示成强操作 |

### 4. 历史验证口径

- 历史结果只展示 `命中`、`未命中`、`待验证`，不要恢复“盘整未触发”。
- `10:00` 早盘研判用当日收盘价验证：看涨且收盘价高于研判价为命中，看跌且收盘价低于研判价为命中。
- `14:30` 收盘前研判用次日 `10:00` 附近行情快照验证，不用次日开盘价。
- 次日验证优先取 `data_time >= 次日 10:00` 的第一条快照；缺失时可回退到 `09:55` 到 `10:00` 之间最接近 `10:00` 的快照。
- 如果验证价缺失，保持 `待验证`，不要猜测结果。
- 统计准确率时只计算已验证记录，`待验证` 不进入分母。

### 5. 前端展示原则

- 页面必须解释“信心度/信号强度不是概率”。
- `confidence < 30` 展示为弱信号，避免误导用户直接操作。
- `30 <= confidence < 60` 展示为中等信号，提示结合 K 线和成交量确认。
- `confidence >= 60` 才展示为强信号，但仍要提示止损。
- 新增指标时优先追加到信号通知或证据/风险列表，不要先改 API schema。
- 历史页表格内容搜索应覆盖当前可见字段：代码、名称、研判时段、保存时间、方向、信心度、价格、验证结果。

### 6. 验证

```powershell
# 后端技术研判回归
cd D:\gongju\gplay\server
python -m pytest tests/test_analysis.py tests/test_task_scheduler.py -v

# 调度时间检查：应包含 10:00 和 14:30
python -c "from src.services.task_scheduler import TaskScheduler; s=TaskScheduler(); s._register_jobs(); print([job.id + ':' + str(job.trigger) for job in s.scheduler.get_jobs() if 'technical' in job.id])"

# 技术研判接口检查
python -c "import urllib.request,json; d=json.loads(urllib.request.urlopen('http://127.0.0.1:8008/api/stocks/000630/technical-analysis',timeout=30).read()); print(d['priceAtAnalysis'], d['direction'], d['confidence'], d['signals'])"

# 做T价位检查
python -c "import urllib.request,json; d=json.loads(urllib.request.urlopen('http://127.0.0.1:8008/api/stocks/000338/t-analysis',timeout=30).read()); print(d['levels']['currentPrice'], d['signals']['buyPrice'], d['signals']['sellPrice'], d['signals']['stopLoss'])"

# 同日同时段重复保存检查
python -c "from src.db.database import SessionLocal; from src.handlers.technical_analysis import save_technical_analysis_for_symbol; from src.models import TechnicalRecord; db=SessionLocal(); before=db.query(TechnicalRecord).filter(TechnicalRecord.symbol=='000338').count(); save_technical_analysis_for_symbol(db,'000338'); after=db.query(TechnicalRecord).filter(TechnicalRecord.symbol=='000338').count(); print(before, after); db.close()"

# 前端构建
cd D:\gongju\gplay\frontend
npm run build
```

## 验收标准

- [ ] 技术研判接口返回 `direction`、`confidence`、`signals`、`keyEvidence`、`riskWarning`。
- [ ] 新增研判只返回 `UP` 或 `DOWN`，不返回 `SIDEWAYS`。
- [ ] 当前价接近最新 K 线价，不出现明显旧价。
- [ ] 信号价满足方向排序约束。
- [ ] 做T买入价、卖出价、止损价贴近当前价，不出现 27 元股票给 17 元买点这类旧价。
- [ ] 页面清楚解释信心度不是概率。
- [ ] 弱信号不会被展示成强操作建议。
- [ ] 预览不自动入历史，保存按钮能写入历史。
- [ ] 关注列表股票会在 `10:00` 和 `14:30` 自动采集并写入历史。
- [ ] 同日同股票同时段重复保存后，历史条数不增加。
- [ ] 历史时间展示研判时段（早盘 10:00 / 收盘前 14:30）和实际保存时间。
- [ ] 历史验证只展示 `命中`、`未命中`、`待验证`，准确率只统计已验证记录。
- [ ] 收盘前研判按次日 `10:00` 附近快照验证，缺失数据保持 `待验证`。
- [ ] 历史页表格搜索能按代码、名称、方向、结果、时间、信心度和价格筛选。
- [ ] `python -m pytest tests/test_analysis.py tests/test_task_scheduler.py -v` 成功。
- [ ] `npm run build` 成功。

## 常见错误

| 问题 | 原因 | 处理 |
|---|---|---|
| 页面白屏 | 后端未返回 `keyEvidence`/`riskWarning`，前端直接 map | 前端使用空数组兜底，后端从指标 JSON 补齐 |
| 价格远离现价 | K 线顺序未排序，旧 close/旧 MA 被当成当前参考 | 计算前按 `date` 升序排序，再用 `closes[-1]` |
| 做T买点离谱 | 当前价和 MA/ATR 的时间序列不一致 | 做T内部排序 K 线、用实时价覆盖最新 close，并限制买点贴近现价 |
| 止损方向错误 | 未区分看涨/看跌排序 | 按 `UP`/`DOWN` 分别强制排序 |
| 信心度误解 | 用户把强度当概率 | 文案写明“不是涨跌概率” |
| 弱看跌像强卖出 | 只显示方向不显示强弱 | 增加弱/中/强信号通知 |
| 历史长期待验证 | 没有精确 `10:00` 快照 | 允许使用 `09:55` 到 `10:00` 内最接近 `10:00` 的快照 |
| 准确率被待验证稀释 | 把未验证记录放进分母 | 只统计 `is_correct` 为 True/False 的记录 |
| 恢复盘整口径 | 沿用旧 `SIDEWAYS`/“盘整未触发”文案 | 新增研判只保留看涨/看跌，结果只保留命中/未命中/待验证 |
